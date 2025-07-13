import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import io
import base64
import json

# כדי למנוע הצגת חלונות matplotlib בעת הרצת קוד בשרת
plt.switch_backend('Agg')

def summarize_csv(filepath: str) -> str:
    try:
        # ודא שהקידוד נכון, אחרת עלולות להיות בעיות בטעינת קבצי CSV בעברית
        df = pd.read_csv(filepath, encoding='utf-8')
        summary = {
            "columns": list(df.columns),
            "num_rows": len(df),
            "num_missing": int(df.isnull().sum().sum()),
            "data_types": {col: str(df[col].dtype) for col in df.columns} # הוספת סוגי נתונים
        }
        # שינוי כאן: המרה ל-JSON string
        return json.dumps(summary, ensure_ascii=False, indent=2)
    except UnicodeDecodeError:
        try: # ניסיון נוסף עם קידוד נפוץ אחר
            df = pd.read_csv(filepath, encoding='windows-1255')
            summary = {
                "columns": list(df.columns),
                "num_rows": len(df),
                "num_missing": int(df.isnull().sum().sum()),
                "data_types": {col: str(df[col].dtype) for col in df.columns}
            }
            # שינוי כאן: המרה ל-JSON string
            return json.dumps(summary, ensure_ascii=False, indent=2)
        except Exception as e:
            return f"שגיאה בקריאת הקובץ: לא ניתן לפענח את הקידוד. {str(e)}"
    except Exception as e:
        return f"שגיאה בקריאת הקובץ: {str(e)}"

# שאר הפונקציות בקובץ processor.py נשארות כפי שהן
def execute_analysis_code(code: str, df: pd.DataFrame = None):
    # נגדיר כאן משתנים גלובליים שקוד המודל יוכל לגשת אליהם
    # **אזהרה: הרצת קוד שנוצר ע"י מודל שפה היא מסוכנת! יש להשתמש בזהירות ובסביבה מבוקרת.**
    local_scope = {
        "pd": pd,
        "plt": plt,
        "sns": sns,
        "df": df,  # נשדר את ה-DataFrame כך שהקוד יוכל לעבוד עליו
        "json": json, # נוסיף גישה ל-json אם נרצה שהמודל ייצר JSON
        "chart_config": None # המודל יוכל להגדיר כאן אובייקט Chart.js JSON
    }

    try:
        # נריץ את הקוד, וכל מה שהקוד ייצור ב-local_scope יהיה נגיש לאחר מכן
        exec(code, {"__builtins__": __builtins__}, local_scope)

        result_message = "הקוד רץ בהצלחה."
        chart_data_uri = None

        # אם הקוד יצר chart_config, נחזיר אותו. זו הדרך המועדפת לגרפים.
        if local_scope.get("chart_config"):
            try:
                # לוודא שזה JSON תקין
                json.dumps(local_scope["chart_config"])
                return {"message": result_message, "chartConfig": local_scope["chart_config"]}
            except TypeError as e:
                return {"message": f"הקוד רץ, אך יש שגיאה בפורמט ה-JSON של הגרף: {str(e)}", "chartConfig": None}

        # אם המודל יצר גרף באמצעות matplotlib (פחות מומלץ, אבל אפשרי), נשמור אותו כ-PNG בזיכרון
        # ונוודא שלא נותרו גרפים פתוחים
        if plt.get_fignums(): # בדיקה האם יש גרפים פתוחים
            buf = io.BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight')
            buf.seek(0)
            chart_data_uri = "data:image/png;base64," + base64.bclib.encodebytes(buf.getvalue()).decode('ascii')
            plt.close('all') # סגור את כל הגרפים כדי למנוע זליגת זיכרון

        return {"message": result_message, "chartImageUri": chart_data_uri}

    except Exception as e:
        # ודא סגירת גרפים גם במקרה של שגיאה
        plt.close('all')
        return {"message": f"שגיאה בהרצת קוד: {str(e)}", "chartImageUri": None, "chartConfig": None}