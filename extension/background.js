chrome.action.onClicked.addListener(() => {
    fetch("https://tickets-2-bger.onrender.com/log_user", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            descripcion: "Ejemplo desde extensión",
            problema: "No me anda el sistema"
        })
    })
    .then(response => response.text())
    .then(data => {
        console.log("Respuesta del servidor:", data);
    })
    .catch(error => {
        console.error("Error al enviar el ticket:", error);
    });
});
