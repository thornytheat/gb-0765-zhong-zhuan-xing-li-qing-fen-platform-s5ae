export function attachTail() {
  const tail = document.querySelector('#scan-tail');
  const pause = document.querySelector('#pause');
  const rows = Array.from(document.querySelector('#tail-source').content.children);
  let cursor = Math.min(7, rows.length);
  let paused = false;
  tail.append(...rows.slice(0, cursor));
  if (!rows.length) tail.textContent = '无采信扫件。';
  pause.addEventListener('click', () => {
    paused = !paused;
    pause.setAttribute('aria-pressed', String(paused));
    pause.textContent = paused ? '恢复扫描尾' : '暂停扫描尾';
  });
  const timer = setInterval(() => {
    if (cursor >= rows.length) { clearInterval(timer); return; }
    if (paused) return;
    tail.append(rows[cursor++]);
    tail.scrollTop = tail.scrollHeight;
  }, 900);
}
