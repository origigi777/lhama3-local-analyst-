import subprocess

def query_llama3(prompt: str) -> str:
    try:
        result = subprocess.run(
            ["ollama", "run", "llama3"],
            input=prompt.encode('utf-8'),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=12000 # זמן המתנה הוגדל ל-120 שניות (2 דקות)
        )
        output = result.stdout.decode('utf-8')
        return output.strip()
    except Exception as e:
        # בדיקה האם השגיאה נובעת מחריגת זמן תגובה
        if isinstance(e, subprocess.TimeoutExpired):
            return f"[שגיאה: המודל חרג מזמן התגובה ({e.timeout} שניות). נסה שוב או עם שאלה פשוטה יותר.]"
        else:
            return f"[שגיאה בשיחה עם המודל: {str(e)}]"