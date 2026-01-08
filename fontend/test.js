const form = document.getElementById("testForm");
const result = document.getElementById("result");
const button = form.querySelector("button");

// 🔴 CHANGE THIS TO YOUR RAILWAY BACKEND URL
const API_URL = "https://vartiss-backend-production.up.railway.app/send-mail";

form.addEventListener("submit", async (e) => {
  e.preventDefault();

  button.disabled = true;
  button.innerText = "Sending...";

  const payload = {
    name: document.getElementById("name").value.trim(),
    email: document.getElementById("email").value.trim(),
    phone: document.getElementById("phone").value.trim(),
    message: document.getElementById("message").value.trim(),
    source: document.getElementById("source").value
  };

  try {
    const res = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const data = await res.json();

    if (data.success) {
      result.style.color = "lightgreen";
      result.innerText = "✅ Submitted successfully (check email / Excel)";
      form.reset();
    } else {
      result.style.color = "orange";
      result.innerText = "⚠️ Backend returned error";
    }

  } catch (err) {
    result.style.color = "red";
    result.innerText = "❌ Network error (check backend)";
  }

  button.disabled = false;
  button.innerText = "Send Test";
});
