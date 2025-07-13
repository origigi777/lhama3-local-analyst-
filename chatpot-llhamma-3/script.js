let csvFileInput, statusDisplay, chatbox, userMessageInput, sendButton,
    apiKeyStatus, apiKeyLoadingBar, fileLoadingBar;

let csvData = []; // זה לא יהיה בשימוש ישיר לניתוח, רק לטעינה ראשונית
let headers = [];
let fullCsvText = ''; // לא יהיה בשימוש לניתוח, רק לפרסום ראשוני אם המודל יצטרך
let isModelReady = false;
let isDataLoaded = false;
const MAX_CONTEXT_CHARS = 70000; // פחות רלוונטי כשהעיבוד בשרת
const MAX_ROWS_IN_CONTEXT = 800; // פחות רלוונטי כשהעיבוד בשרת

const LOCAL_LLM_ENDPOINT = "http://localhost:8000/api/ask";
const UPLOAD_ENDPOINT = "http://localhost:8000/api/upload"; // נקודת קצה חדשה להעלאה

document.addEventListener('DOMContentLoaded', () => {
    csvFileInput = document.getElementById('csvFile');
    statusDisplay = document.getElementById('status');
    chatbox = document.getElementById('chatbox');
    userMessageInput = document.getElementById('userMessage');
    sendButton = document.getElementById('sendButton');
    apiKeyStatus = document.getElementById('apiKeyStatus');
    apiKeyLoadingBar = document.getElementById('apiKeyLoadingBar');
    fileLoadingBar = document.getElementById('fileLoadingBar');

    if (csvFileInput) csvFileInput.addEventListener('change', handleFileUpload);
    if (sendButton && userMessageInput) {
        sendButton.addEventListener('click', handleSendMessage);
        userMessageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !sendButton.disabled) handleSendMessage();
        });
    }

    updateStatusText(apiKeyStatus, "המודל המקומי זמין ומוכן.", "success");
    isModelReady = true;
    hideLoadingBar(apiKeyLoadingBar);
    checkEnableSend();
});

function updateStatusText(element, message, type = 'info') {
    if (element) {
        element.textContent = message;
        element.className = `status-${type}`;
    }
}
function showLoadingBar(barElement) { if (barElement) barElement.style.display = 'block'; }
function hideLoadingBar(barElement) { if (barElement) barElement.style.display = 'none'; }

function checkEnableSend() {
    const enabled = isModelReady && isDataLoaded;
    if (userMessageInput) userMessageInput.disabled = !enabled;
    if (sendButton) sendButton.disabled = !enabled;
    if (userMessageInput) {
        if (enabled) userMessageInput.placeholder = "שאל אותי על נתוני ה-CSV...";
        else if (!isModelReady) userMessageInput.placeholder = "המודל לא מוכן...";
        else userMessageInput.placeholder = "אנא טען קובץ CSV...";
    }
}

async function handleFileUpload(event) {
    const file = event.target.files[0];
    isDataLoaded = false;
    checkEnableSend();
    if (!file) {
        updateStatusText(statusDisplay, "לא נבחר קובץ.", "error");
        return;
    }
    if (!file.name.toLowerCase().endsWith('.csv')) {
        updateStatusText(statusDisplay, "אנא טען קובץ CSV בלבד.", "error");
        csvFileInput.value = '';
        return;
    }

    updateStatusText(statusDisplay, `מעלה את הקובץ: ${file.name}...`, "loading");
    showLoadingBar(fileLoadingBar);
    csvData = []; headers = []; fullCsvText = ''; // לא נשתמש בזה ב-frontend לניתוח
    if (chatbox) chatbox.innerHTML = '';

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch(UPLOAD_ENDPOINT, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `שגיאת שרת: ${response.status}`);
        }

        const result = await response.json();
        const filename = result.filename;
        headers = result.headers; // קבל את הכותרות מהשרת
        const numRows = result.num_rows; // קבל את מספר השורות מהשרת

        currentLoadedFilename = filename; // שמור את שם הקובץ שנטען בהצלחה

        updateStatusText(statusDisplay, `קובץ "${filename}" נטען בהצלחה (${numRows} שורות). מוכן לשאלות!`, "success");
        isDataLoaded = true;
        addMessage({ textResponse: `קובץ "${filename}" נטען בהצלחה. נטענו ${numRows} שורות עם הכותרות: ${headers.join(', ')}.` });

    } catch (error) {
        updateStatusText(statusDisplay, `שגיאה בהעלאת הקובץ: ${error.message}`, "error");
        csvFileInput.value = ''; // נקה את בחירת הקובץ
    } finally {
        hideLoadingBar(fileLoadingBar);
        checkEnableSend();
    }
}

// הפונקציות parseCSV ו-detectDelimiter ו-getCSVContextForPrompt לא נחוצות יותר ב-frontend לניתוח
// הן היו עבור שליחת הקונטקסט ל-LLM מ-JS, אך כעת הכל מטופל בשרת

let currentLoadedFilename = null; // משתנה לשמירת שם הקובץ הנוכחי

async function handleSendMessage() {
    const messageText = userMessageInput.value.trim();
    if (!messageText || !isModelReady || !isDataLoaded) return;
    addMessage({ textResponse: messageText }, 'user');
    userMessageInput.value = '';
    userMessageInput.disabled = true;
    sendButton.disabled = true;

    const thinking = addMessage({ textResponse: "מעבד בקשה..." }, 'bot');
    if (thinking) thinking.classList.add('thinking');

    try {
        const botResponse = await getLlamaResponse(messageText);
        if (chatbox && thinking && chatbox.contains(thinking)) chatbox.removeChild(thinking);
        addMessage(botResponse, 'bot');
    } catch (error) {
        console.error("Error getting Llama response:", error);
        if (chatbox && thinking && chatbox.contains(thinking)) chatbox.removeChild(thinking);
        addMessage({ textResponse: `שגיאה בתקשורת עם המודל: ${error.message}` }, 'bot');
    } finally {
        checkEnableSend();
    }
}

async function getLlamaResponse(query) {
    const payload = {
        question: query,
        filename: currentLoadedFilename // שלח את שם הקובץ הנוכחי לשרת
    };

    const response = await fetch(LOCAL_LLM_ENDPOINT, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    });

    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`שגיאת שרת: ${response.status} ${errorText}`);
    }

    const data = await response.json();
    console.log("Server response data:", data); // לניפוי באגים

    // *** תיקון: הסרת קטע הקוד הבעייתי שחיפש מרקרים בטקסט ***
    // במקום זאת, ניגש ישירות למאפיינים chartConfig ו-chartImageUri באובייקט ה-data
    return {
        textResponse: data.answer || "לא התקבלה תשובה מהשרת.",
        chartConfig: data.chartConfig || null,
        chartImageUri: data.chartImageUri || null
    };
}

function addMessage(response, sender = 'bot') {
    if (!chatbox) return null;
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message', `${sender}-message`);

    // *** תיקון: וודא ש-response.textResponse קיים לפני השימוש ***
    if (response.textResponse) {
        const text = document.createElement('div');
        text.innerHTML = response.textResponse.replace(/\n/g, '<br>'); // תמיכה במעברי שורה
        messageDiv.appendChild(text);
    }

    // טיפול ב-Chart.js JSON
    if (sender === 'bot' && response.chartConfig) {
        const chartId = `chart-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`;
        const chartWrapper = document.createElement('div');
        chartWrapper.classList.add('chart-wrapper');
        const canvas = document.createElement('canvas');
        canvas.id = chartId;
        chartWrapper.appendChild(canvas);
        messageDiv.appendChild(chartWrapper);

        setTimeout(() => {
            try {
                // וודא שאובייקט ה-Chart.js תקין
                if (response.chartConfig.type && response.chartConfig.data) {
                    response.chartConfig.options = response.chartConfig.options || {};
                    response.chartConfig.options.maintainAspectRatio = false; // חשוב לשליטה בגודל
                    new Chart(document.getElementById(chartId), response.chartConfig);
                } else {
                    chartWrapper.innerHTML = `<p style="color:red;">שגיאה: הגדרת תרשים לא תקינה מהמודל.</p>`;
                }
            } catch (e) {
                console.error("Chart.js rendering error:", e);
                chartWrapper.innerHTML = `<p style="color:red;">שגיאה בתרשים: ${e.message}</p>`;
            }
        }, 100);
    }
    // טיפול בתרשים כתמונה ב-base64
    else if (sender === 'bot' && response.chartImageUri) {
        const imageWrapper = document.createElement('div');
        imageWrapper.classList.add('chart-wrapper'); // נשתמש באותו CSS
        const img = document.createElement('img');
        img.src = response.chartImageUri;
        img.alt = "Generated Chart";
        img.style.maxWidth = "100%";
        img.style.height = "auto";
        imageWrapper.appendChild(img);
        messageDiv.appendChild(imageWrapper);
    }


    chatbox.appendChild(messageDiv);
    chatbox.scrollTop = chatbox.scrollHeight;
    return messageDiv;
}