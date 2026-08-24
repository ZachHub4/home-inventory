(function () {
  const video = document.getElementById("scan-video");
  const canvas = document.getElementById("scan-canvas");
  const status = document.getElementById("scan-status");
  const startBtn = document.getElementById("scan-start");
  const ctx = canvas.getContext("2d", { willReadFrequently: true });

  let stopped = false;
  let stream = null;

  function setStatus(text, isError) {
    status.textContent = text;
    status.classList.toggle("scan-error", !!isError);
  }

  function disableCamera(message) {
    setStatus(message, true);
    video.style.display = "none";
    if (startBtn) startBtn.style.display = "none";
    document.getElementById("manual-entry").classList.add("prominent");
  }

  function releaseCamera() {
    if (stream) {
      stream.getTracks().forEach((t) => t.stop());
      stream = null;
    }
  }

  function handleCode(data) {
    if (stopped) return;
    stopped = true;
    releaseCamera();
    setStatus("Found bin: " + data + " — opening...");
    const match = data.trim().match(/BIN-[A-F0-9]+/i);
    const code = match ? match[0].toUpperCase() : data.trim();
    window.location.href = "/bin/" + encodeURIComponent(code);
  }

  function tick() {
    if (stopped || !stream) return;
    if (video.readyState === video.HAVE_ENOUGH_DATA) {
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
      const result = jsQR(imageData.data, imageData.width, imageData.height);
      if (result && result.data) {
        handleCode(result.data);
        return;
      }
    }
    requestAnimationFrame(tick);
  }

  function startCamera() {
    setStatus("Starting camera...");
    if (startBtn) startBtn.disabled = true;

    navigator.mediaDevices
      .getUserMedia({ video: { facingMode: "environment" } })
      .then((s) => {
        stream = s;
        video.srcObject = s;
        video.setAttribute("playsinline", true);
        video.play();
        video.style.display = "";
        if (startBtn) startBtn.style.display = "none";
        setStatus("Point the camera at a bin's QR label.");
        requestAnimationFrame(tick);
      })
      .catch((err) => {
        if (startBtn) {
          startBtn.disabled = false;
          startBtn.textContent = "Try camera again";
        }
        if (err && (err.name === "NotAllowedError" || err.name === "SecurityError")) {
          setStatus(
            "Camera access was denied. Allow it when prompted, or enter the bin code below.",
            true
          );
        } else {
          setStatus("Couldn't start the camera: " + (err && err.message) + ".", true);
        }
      });
  }

  // Browsers only expose the camera API over HTTPS (or on localhost). Over plain
  // HTTP on a LAN address, navigator.mediaDevices is undefined entirely - which
  // looks like "no camera support" but is really a page-security restriction.
  if (!window.isSecureContext) {
    disableCamera(
      "Scanning needs a secure (HTTPS) connection. This page is served over " +
        "plain HTTP, so the browser blocks camera access. Enter the bin code below instead."
    );
    return;
  }

  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    disableCamera("This browser doesn't support camera access. Enter the bin code below instead.");
    return;
  }

  // Wait for a deliberate tap before touching the camera. Requesting it on page
  // load means the permission prompt fires even when someone is just passing
  // through this page - iOS asks again on every app launch regardless.
  video.style.display = "none";
  setStatus("Tap below to start the camera, or enter a bin code.");
  startBtn.addEventListener("click", startCamera);

  // Free the camera when leaving, so the indicator light does not linger.
  window.addEventListener("pagehide", releaseCamera);
})();
