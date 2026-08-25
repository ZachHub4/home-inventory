(function () {
  const video = document.getElementById("scan-video");
  const status = document.getElementById("scan-status");
  const startBtn = document.getElementById("scan-start");
  const lookupBox = document.getElementById("lookup-online");
  const fieldBarcode = document.getElementById("field-barcode");
  const fieldName = document.getElementById("field-name");
  const found = document.getElementById("barcode-found");

  let reader = null;
  let running = false;

  function setStatus(text, isError) {
    status.textContent = text;
    status.classList.toggle("scan-error", !!isError);
  }

  // The lookup preference is a local choice, so it lives in the browser.
  lookupBox.checked = localStorage.getItem("barcodeLookup") === "1";
  lookupBox.addEventListener("change", () => {
    localStorage.setItem("barcodeLookup", lookupBox.checked ? "1" : "0");
  });

  function stopCamera() {
    if (reader) {
      reader.reset();
      running = false;
    }
  }

  async function onBarcode(text) {
    if (!running) return;
    stopCamera();
    video.style.display = "none";
    startBtn.style.display = "";
    startBtn.textContent = "Scan another";
    startBtn.disabled = false;

    fieldBarcode.value = text;
    found.hidden = false;
    found.textContent = `Barcode ${text}`;
    setStatus("Barcode captured.");

    if (!lookupBox.checked) {
      fieldName.focus();
      return;
    }

    setStatus("Looking up the product name...");
    try {
      const res = await fetch(`/barcode-lookup?code=${encodeURIComponent(text)}`);
      const data = await res.json();
      if (data.found) {
        fieldName.value = data.name;
        found.textContent = `Barcode ${text} — ${data.name}`;
        setStatus("Found it. Check the name, then add.");
      } else {
        setStatus(data.error || "No name found — type it in yourself.");
        fieldName.focus();
      }
    } catch (err) {
      setStatus("Lookup failed — type the name in yourself.");
      fieldName.focus();
    }
  }

  function startCamera() {
    startBtn.disabled = true;
    setStatus("Starting camera...");

    const hints = new Map();
    const formats = [
      ZXing.BarcodeFormat.UPC_A,
      ZXing.BarcodeFormat.UPC_E,
      ZXing.BarcodeFormat.EAN_13,
      ZXing.BarcodeFormat.EAN_8,
      ZXing.BarcodeFormat.CODE_128,
      ZXing.BarcodeFormat.CODE_39,
      ZXing.BarcodeFormat.ITF,
    ];
    hints.set(ZXing.DecodeHintType.POSSIBLE_FORMATS, formats);

    reader = new ZXing.BrowserMultiFormatReader(hints);
    running = true;
    video.style.display = "";

    reader
      .decodeFromConstraints(
        { video: { facingMode: "environment" } },
        video,
        (result, err) => {
          if (result) onBarcode(result.getText());
        }
      )
      .then(() => {
        startBtn.style.display = "none";
        setStatus("Point the camera at the product's barcode.");
      })
      .catch((err) => {
        running = false;
        startBtn.disabled = false;
        startBtn.textContent = "Try camera again";
        video.style.display = "none";
        if (err && (err.name === "NotAllowedError" || err.name === "SecurityError")) {
          setStatus("Camera access was denied. Type the item in below instead.", true);
        } else {
          setStatus("Couldn't start the camera: " + (err && err.message) + ".", true);
        }
      });
  }

  if (!window.isSecureContext || !navigator.mediaDevices) {
    video.style.display = "none";
    startBtn.style.display = "none";
    setStatus(
      "Scanning needs a secure (HTTPS) connection. Type the item in below instead.",
      true
    );
    return;
  }

  video.style.display = "none";
  setStatus("Tap below to scan a barcode, or just type the item in.");
  startBtn.addEventListener("click", startCamera);
  window.addEventListener("pagehide", stopCamera);
})();
