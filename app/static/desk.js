import {attachTail} from './tail.js';
attachTail();
const feedback = document.querySelector('#feedback');
const sample = document.querySelector('#sample');
const key = location.pathname.split('/').at(-1) || 'ledger';
async function archive(button, url, body) {
  button.disabled = true;
  feedback.textContent = '正在复算…';
  try {
    const response = await fetch(url, {method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(body)});
    const data = await response.json();
    if (!response.ok) throw new Error(data.message);
    feedback.textContent = data.reused ? '复算一致 · 复用归档' : '归档完成';
    if (button.id !== 'rerun') location.assign(`/desk/${key}?${new URLSearchParams({run: data.id, sample: sample.value})}`);
  } catch (error) {
    feedback.textContent = error.message || '复算失败，请重试';
  } finally {
    button.disabled = false;
  }
}
sample.addEventListener('change', () => location.assign(`/desk/${key}?sample=${sample.value}`));
document.querySelector('#run-form').addEventListener('submit', event => {
  event.preventDefault();
  archive(document.querySelector('#archive-button'), '/api/archive', {sample: sample.value});
});
document.querySelector('#rerun')?.addEventListener('click', event => archive(event.currentTarget, `/api/archive/${event.currentTarget.dataset.run}/rerun`));
document.querySelector('#bag-filter')?.addEventListener('input', event => {
  for (const row of document.querySelectorAll('#bag-list [data-tag]')) row.hidden = !row.dataset.tag.includes(event.target.value.trim());
});
async function call(button, url, body) {
  button.disabled = true;
  try {
    const response = await fetch(url, {method: 'POST', headers: {'Content-Type':'application/json'}, body: body ? JSON.stringify(body) : undefined});
    const data = await response.json();
    if (!response.ok) throw new Error(data.message);
    feedback.textContent = url.endsWith('/revoke') ? '收件权限已撤回 · 旧链接失效' : '证据已签发 · 限本站下载';
    const params = new URLSearchParams(location.search);
    params.set('station', button.dataset.station);
    location.assign(`${location.pathname}?${params}`);
  } catch (error) {
    feedback.textContent = error.message || '操作失败，请重试';
    button.disabled = false;
  }
}
document.querySelectorAll('#station-list .issue, #station-list .revoke').forEach(button => {
  const run = button.dataset.run, station = encodeURIComponent(button.dataset.station);
  const url = button.classList.contains('issue')
    ? `/api/evidence/${run}/stations/${station}`
    : `/api/evidence/${run}/stations/${station}/revoke`;
  button.addEventListener('click', () => call(button, url));
});
