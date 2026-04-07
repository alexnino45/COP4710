const createUserForm = document.getElementById("create-user-form");
const resultBox = document.getElementById("result");

if (createUserForm && resultBox) {
    createUserForm.addEventListener("submit", async (event) => {
        event.preventDefault();

        const payload = {
            name: document.getElementById("name").value,
            email: document.getElementById("email").value,
        };

        const response = await fetch("/users", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        const data = await response.json();
        resultBox.textContent = JSON.stringify(data, null, 2);
    });
}
