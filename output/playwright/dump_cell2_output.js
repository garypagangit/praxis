async page => {
  const text = await page
    .getByRole('region', { name: /Cell 2 output/ })
    .textContent();
  throw new Error((text || 'NO OUTPUT').slice(0, 8000));
}
