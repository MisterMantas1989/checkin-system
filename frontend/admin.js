
function fetchLogs() {
    const date = document.getElementById('date').value;
    if (!date) {
        alert("Vänligen välj ett datum.");
        return;
    }

    fetch(`http://127.0.0.1:5000/logs/${date}`)
        .then(res => res.json())
        .then(data => {
            const table = document.getElementById("logTable").querySelector("tbody");
            table.innerHTML = "";
            data.logs.forEach(row => {
                const tr = document.createElement("tr");
                row.forEach(cell => {
                    const td = document.createElement("td");
                    td.innerText = cell;
                    tr.appendChild(td);
                });
                table.appendChild(tr);
            });
        })
        .catch(err => {
            alert("Kunde inte hämta loggar. Kontrollera att servern körs.");
            console.error(err);
        });
}
