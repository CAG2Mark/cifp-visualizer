function $(val) {
    return document.getElementById(val);
}

let sidArea = $("sidebar-sid-area");
let starArea = $("sidebar-star-area");
let appchArea = $("sidebar-approach-area");

let sidBtn = $("proc-sid");
let starBtn = $("proc-star");
let appchBtn = $("proc-approach");

sidBtn.addEventListener("change", () => {
    sidArea.classList.remove("hidden");
    starArea.classList.add("hidden");
    appchArea.classList.add("hidden");
})

starBtn.addEventListener("change", () => {
    sidArea.classList.add("hidden");
    starArea.classList.remove("hidden");
    appchArea.classList.add("hidden");
})

appchBtn.addEventListener("change", () => {
    sidArea.classList.add("hidden");
    starArea.classList.add("hidden");
    appchArea.classList.remove("hidden");
})

let airportArea = $("sidebar-airport-area");
let legsArea = $("sidebar-legs-area");

$("back-button").addEventListener("click", () => {
    airportArea.classList.remove("hidden");
    legsArea.classList.add("hidden");
})

let popupArea = $("popup-cover");
let popupLicense = $("license-popup");
let popupInvalid = $("invalid-airport-popup");
let popupInvalidText = $("invalid-airport-popup-text");

function hidePopups() {
    popupArea.classList.add("hidden");
    popupLicense.classList.add("hidden");
    popupInvalid.classList.add("hidden");
}

$("close-license-button").addEventListener("click", () => {
    hidePopups();
});

$("legal-info-button").addEventListener("click",() => {
    popupArea.classList.remove("hidden");
    popupLicense.classList.remove("hidden");
    popupInvalid.classList.add("hidden");
})
