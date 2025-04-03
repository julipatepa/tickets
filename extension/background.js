chrome.action.onClicked.addListener(() => {
    chrome.tabs.create({ url: "http://127.0.0.1:5000" });  // Cambia esto si lo tienes en un servidor
});
