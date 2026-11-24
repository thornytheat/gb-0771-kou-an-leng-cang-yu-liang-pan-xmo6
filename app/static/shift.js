import {selectLot} from './tracks.js';
selectLot();
const dataset = document.querySelector('#dataset');
const status = document.querySelector('#status');
dataset.addEventListener('change', () => location.assign(`/view/${document.body.dataset.view}?sample=${dataset.value}`));
async function file(button, path, payload) {
  button.disabled = true;
  status.textContent = '复算中…';
  try {
    const response = await fetch(path, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)});
    const result = await response.json();
    if (!response.ok) throw new Error(result.message);
    status.textContent = result.reused ? '复算一致' : '归档完成';
    if (button.id === 'file-receipt') location.assign(`/view/history?${new URLSearchParams({receipt:result.id,sample:dataset.value})}`);
  } catch (error) {
    status.textContent = error.message || '请重试归档';
  } finally { button.disabled = false; }
}
document.querySelector('#docket').addEventListener('submit', event => {
  event.preventDefault(); file(event.submitter, '/api/receipts', {sample:dataset.value});
});
document.querySelector('#refresh')?.addEventListener('click', event => file(event.currentTarget, `/api/receipts/${event.currentTarget.dataset.id}/refresh`, null));
