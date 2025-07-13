from flask import Flask, request, jsonify
from flask_cors import CORS
from llama_interface import query_llama3
from processor import summarize_csv, execute_analysis_code
import os
import pandas as pd
import json

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
# צור את תיקיית ההעלאות אם אינה קיימת
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# נשתמש במילון כדי לשמור את ה-DataFrame בזיכרון לפי שם קובץ
# **שים לב: זו לא הדרך הכי יעילה לניהול זיכרון ב-production.**
# עבור פרויקט קטן או POC זה יכול לעבוד. ב-production תצטרך אסטרטגיית קאשינג טובה יותר
# או טעינת נתונים מבסיס נתונים.
loaded_dataframes = {}


@app.route("/api/ask", methods=["POST"])
def ask():
    data = request.json
    question = data.get("question", "")
    filename = data.get("filename", "")

    # המרה מפורשת למחרוזת למקרה שאחד מהם אינו מחרוזת מסיבה כלשהי
    question_str = str(question)
    filename_str = str(filename)

    # הדפסת ניפוי באגים
    print(f"DEBUG app.py: Received question: {question_str}, filename: {filename_str}")

    if not question_str:
        return jsonify({"error": "Missing question"}), 400

    current_df = None
    if filename_str:
        filepath = os.path.join(UPLOAD_FOLDER, filename_str)
        if not os.path.exists(filepath):
            return jsonify({"error": "File not found"}), 404

        # ננסה לטעון את ה-DataFrame אם הוא לא טעון כבר
        if filename_str not in loaded_dataframes:
            try:
                # ננסה עם קידודים שונים כפי שמוגדר ב-processor.py
                loaded_dataframes[filename_str] = pd.read_csv(filepath, encoding='utf-8')
            except UnicodeDecodeError:
                loaded_dataframes[filename_str] = pd.read_csv(filepath, encoding='windows-1255')
            except Exception as e:
                return jsonify({"error": f"שגיאה בטעינת קובץ ה-CSV: {str(e)}"}), 500

        current_df = loaded_dataframes[filename_str]
        csv_summary =pd.read_csv(filepath, encoding='utf-8')
            #summarize_csv(filepath)  # summarize_csv מחזיר עכשיו JSON string

        # הדפסת ניפוי באגים
        print(f"DEBUG app.py: CSV Summary type: {type(csv_summary)}, value: {csv_summary[:500]}...")

        prompt = f"""
        הנתונים נמצאים ב-DataFrame פייתון בשם 'df'.
        הנה סיכום קובץ הנתונים שהועלה ({filename_str}):
        {csv_summary}

        תן תשובה בעברית על השאלה: "{question_str}
        """
    else:
        # אם אין קובץ, שאל שאלה כללית
        prompt = question_str  # כבר עבר המרה ל-str למעלה

    # הדפסת ניפוי באגים
    print(f"DEBUG app.py: Prompt being sent to Llama (first 1000 chars): {prompt[:1000]}...")

    response_from_llama = query_llama3(prompt)
    print(f"Llama Response: {response_from_llama}")  # לניפוי באגים

    text_answer = response_from_llama
    chart_config_data = None
    chart_image_uri = None  # הוסף משתנה עבור URI של תמונה
    exec_feedback = None

    # חלץ קוד פייתון אם קיים
    if '```python' in response_from_llama:
        try:
            code_start = response_from_llama.find('```python') + len('```python')
            code_end = response_from_llama.find('```', code_start)
            code = response_from_llama[code_start:code_end].strip()

            # נחלץ גם את הטקסט לפני ואחרי הקוד
            text_parts = response_from_llama.split('```python')
            pre_code_text = text_parts[0].strip()
            post_code_text = response_from_llama[code_end + len('```'):].strip()
            text_answer = f"{pre_code_text}\n{post_code_text}".strip()

            # העבר את ה-DataFrame לפונקציית ההרצה
            exec_result = execute_analysis_code(code, df=current_df)
            exec_feedback = exec_result.get("message", "הקוד רץ בהצלחה.")
            chart_config_data = exec_result.get("chartConfig")
            chart_image_uri = exec_result.get("chartImageUri")  # קבל את ה-URI של התמונה

            print(f"Execution Feedback: {exec_feedback}")
        except Exception as e:
            exec_feedback = f"שגיאה בחילוץ או הרצת קוד: {str(e)}"
            text_answer = f"{response_from_llama}\n{exec_feedback}"

    # אם המודל יצר ישר JSON ולא קוד, ננסה לפרסר אותו
    elif '{' in response_from_llama and '}' in response_from_llama:
        try:
            # ננסה לזהות אם המודל יצר ישירות אובייקט Chart.js JSON
            json_start = response_from_llama.find('{')
            json_end = response_from_llama.rfind('}') + 1
            json_str = response_from_llama[json_start:json_end]
            possible_chart_config = json.loads(json_str)
            if 'type' in possible_chart_config and 'data' in possible_chart_config:
                chart_config_data = possible_chart_config
                # נוריד את ה-JSON מהטקסט המקורי
                text_answer = response_from_llama[:json_start].strip() + response_from_llama[json_end:].strip()
        except json.JSONDecodeError:
            pass  # לא היה JSON תקין
        except Exception as e:
            print(f"Error parsing direct JSON from Llama: {e}")

    # אם יש תוצאות קוד אבל לא גרף מוגדר, נוסיף את משוב ההרצה
    if exec_feedback and not chart_config_data and not chart_image_uri and "שגיאה בהרצת קוד" in exec_feedback:
        text_answer += f"\n\n[הערת המערכת: {exec_feedback}]"

    # נחזיר את התשובה, אובייקט ה-Chart.js JSON, ואת תוצאת הרצת הקוד
    return jsonify({
        "answer": text_answer,
        "chartConfig": chart_config_data,
        "chartImageUri": chart_image_uri,  # וודא שזה נשלח ללקוח
        "execution": exec_feedback
    })


@app.route("/api/upload", methods=["POST"])
def upload_csv():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    try:
        file.save(filepath)
        # נטען את הקובץ ל-DataFrame מיד לאחר העלאה
        # זה יאפשר ל-script.js לקבל את כמות השורות והכותרות ישירות
        # וגם למנוע טעינה חוזרת בכל שאילתה (אבל עדיין לא אידיאלי ל-production)
        try:
            df = pd.read_csv(filepath, encoding='utf-8')
        except UnicodeDecodeError:
            df = pd.read_csv(filepath, encoding='windows-1255')

        loaded_dataframes[file.filename] = df  # שמור את ה-DataFrame בזיכרון

        headers = list(df.columns)
        num_rows = len(df)

        return jsonify({
            "message": "File uploaded successfully",
            "filename": file.filename,
            "headers": headers,
            "num_rows": num_rows
        })
    except Exception as e:
        return jsonify({"error": f"שגיאה בשמירת או טעינת הקובץ: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=True, port=8000)