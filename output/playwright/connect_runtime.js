async page => {
  const connectButton = page.getByRole('button', { name: /Connect A100 High-RAM|Connect to a new runtime|Reconnect/i }).first();
  await connectButton.click();
  await page.waitForTimeout(8000);
}
