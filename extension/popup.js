document.getElementById("openTickets").addEventListener("click", () => {
    chrome.tabs.create({ url: "https://tickets-2-bger.onrender.com" });
});
