let currentField = "";

function openEditPopup(field, currentValue) {
    currentField = field;
    document.getElementById("editField").textContent = field.replace("_", " ");
    document.getElementById("newValue").value = currentValue;
    document.getElementById("password").value = "";
    document.getElementById("editPopup").classList.remove("hidden");
}

function closePopup() {
    document.getElementById("editPopup").classList.add("hidden");
}

function confirmEdit() {
    const password = document.getElementById("password").value;
    const newValue = document.getElementById("newValue").value;

    if (!password || !newValue) {
        alert("Please fill in all fields.");
        return;
    }

    // Submit data via AJAX
    fetch(`/update_account`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            field: currentField,
            value: newValue,
            password: password,
        }),
    })
        .then((response) => response.json())
        .then((data) => {
            if (data.success) {
                alert("Updated successfully!");
                location.reload();
            } else {
                alert(data.message);
            }
        });
    closePopup();
}
