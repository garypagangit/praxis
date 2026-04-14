async page => {
  const cell = page.getByRole('region', { name: /Cell 4: Code cell:/ });
  await cell.getByRole('button', { name: 'Run cell' }).click();
  await page.waitForTimeout(5000);
}
