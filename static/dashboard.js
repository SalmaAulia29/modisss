const panel = document.querySelector(".worker-panel");
const countdown = document.querySelector("#countdown");
const refreshSeconds = Number(document.querySelector('meta[name="refresh-seconds"]')?.content || 30);
let secondsRemaining = Number(panel?.dataset.seconds || 0);

function renderCountdown() {
  if (!countdown) return;
  if (secondsRemaining <= 0) {
    countdown.textContent = panel?.querySelector(".status-running") ? "sedang berjalan" : "segera";
    return;
  }
  const hours = Math.floor(secondsRemaining / 3600);
  const minutes = Math.floor((secondsRemaining % 3600) / 60);
  const seconds = secondsRemaining % 60;
  countdown.textContent = [hours, minutes, seconds].map(value => String(value).padStart(2, "0")).join(":");
  secondsRemaining -= 1;
}

renderCountdown();
setInterval(renderCountdown, 1000);
setTimeout(() => window.location.reload(), refreshSeconds * 1000);
