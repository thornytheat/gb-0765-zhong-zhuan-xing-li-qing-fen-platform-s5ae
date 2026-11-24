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
