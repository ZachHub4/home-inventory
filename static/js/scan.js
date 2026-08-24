(function () {
  const video = document.getElementById("scan-video");
  const canvas = document.getElementById("scan-canvas");
  const status = document.getElementById("scan-status");
  const ctx = canvas.getContext("2d", { willReadFrequently: true });

  let stopped = false;

  function setStatus(text, isError) {
    status.textContent = text;
    status.classList.toggle("scan-error", !!isError);
  }

  function disableCamera(message) {
    setStatus(message, true);
    video.style.display = "none";
    document.getElementById("manual-entry").classList.add("prominent");
  }

  function handleCode(data) {
    if (stopped) return;
    stopped = true;
    setStatus("Found bin: " + data + " — opening...");
    const match = data.trim().match(/BIN-[A-F0-9]+/i);
    const code = match ? match[0].toUpperCase() : data.trim();
    window.location.href = "/bin/" + encodeURIComponent(code);
  }

  function tick() {
    if (stopped) return;
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

  navigator.mediaDevices
    .getUserMedia({ video: { facingMode: "environment" } })
    .then((stream) => {
      video.srcObject = stream;
      video.setAttribute("playsinline", true);
      video.play();
      setStatus("Point the camera at a bin's QR label.");
      requestAnimationFrame(tick);
    })
    .catch((err) => {
      if (err && (err.name === "NotAllowedError" || err.name === "SecurityError")) {
        disableCamera(
          "Camera permission was denied. Allow it in your browser settings, or enter the bin code below."
        );
      } else {
        disableCamera("Couldn't start the camera: " + (err && err.message) + ".");
      }
    });
})();
