(function () {
  const video = document.getElementById("scan-video");
  const canvas = document.getElementById("scan-canvas");
  const status = document.getElementById("scan-status");
  const ctx = canvas.getContext("2d", { willReadFrequently: true });

  let stopped = false;

  function setStatus(text) {
    status.textContent = text;
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

  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    setStatus("Camera access isn't supported in this browser.");
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
      setStatus("Couldn't access the camera: " + err.message);
    });
})();
