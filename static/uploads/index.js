document.getElementById("uploadForm").onsubmit = async function(event) {
    event.preventDefault(); // מונע את שליחת הטופס באופן רגיל

    let formData = new FormData(this); // אוסף את הנתונים מהטופס

    try {
        // הצגת הודעה מיידית על העלאת התמונה
        let resultDiv = document.getElementById("result-message");
        resultDiv.innerHTML = "<strong>Uploading image...</strong>";
        resultDiv.style.display = "block";

        // שליחת הנתונים לשרת
        let response = await fetch('/upload', { // יש לוודא שה-URL נכון
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error('Network response was not ok');
        }

        let data = await response.json();

        // הצגת המידע שהתקבל מהשרת
        displayMessage(data);

    } catch (error) {
        console.error("Error:", error);
        let resultDiv = document.getElementById("result-message");
        resultDiv.innerHTML = "<strong>Error:</strong> An error occurred while processing your request.";
        resultDiv.style.display = "block";
    }
};

// פונקציה להצגת הודעה או דוח בדף
function displayMessage(responseData) {
    let message = `
        <strong>Issue:</strong> ${responseData.issue} <br>
        <strong>Message:</strong> ${responseData.message}
    `;

    if (responseData.detected_species.length > 0) {
        message += `<strong>Detected Species:</strong> ${responseData.detected_species.join(", ")}`;
    } else {
        message += `<strong>No species detected.</strong>`;
    }

    if (responseData.change_score) {
        message += `<br><strong>Change Score:</strong> ${responseData.change_score}`;
    }

    let resultDiv = document.getElementById("result-message");
    resultDiv.innerHTML = message;
    resultDiv.style.display = "block"; // מראים את הדיב
}
