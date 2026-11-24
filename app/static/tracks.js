export function selectLot() {
  const controls = [...document.querySelectorAll('[data-lot]')];
  const summaries = [...document.querySelectorAll('[data-summary]')];
  const details = [...document.querySelectorAll('[data-detail]')];
  const title = document.querySelector('#lot-title');
  const description = document.querySelector('#lot-desc');
  for (const button of controls) button.addEventListener('click', () => {
    const lot = button.dataset.lot;
    for (const control of controls) control.setAttribute('aria-pressed', String(control === button));
    for (const summary of summaries) summary.hidden = summary.dataset.summary !== lot;
    for (const row of details) row.hidden = row.dataset.detail !== lot;
    title.textContent = lot;
    description.textContent = button.dataset.description;
  });
}
