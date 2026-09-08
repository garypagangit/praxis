async function refresh() {
  try {
    const response = await fetch('status.json', {cache: 'no-store'});
    if (!response.ok) throw Error(response.status);
    const data = await response.json();
    document.getElementById('updated').textContent = 'Updated ' + data.updated_utc;
    const cards = document.getElementById('cards');
    cards.replaceChildren();
    for (const experiment of data.experiments) {
      const card = document.createElement('article');
      for (const [tag, className, text] of [
        ['div', 'eyebrow', 'Final Praxis ' + experiment.id],
        ['h2', '', experiment.title],
        ['span', 'status', experiment.status],
        ['p', '', experiment.evidence],
        ['p', 'muted', experiment.next]
      ]) {
        const node = document.createElement(tag);
        node.className = className;
        node.textContent = text;
        card.append(node);
      }
      const links = document.createElement('p');
      for (const [key, label] of [['pdf', 'PDF report'], ['docx', 'Word report'], ['report', 'Methods and results']]) {
        if (!experiment[key]) continue;
        if (links.childNodes.length) links.append(' | ');
        const link = document.createElement('a');
        link.href = experiment[key];
        link.textContent = label;
        links.append(link);
      }
      card.append(links);
      cards.append(card);
    }
    document.getElementById('truth').textContent = data.scientific_results_complete +
      ' of 3 experiments have completed independent scientific verification. Infrastructure checks and incomplete runs are not classified as positive or negative.';
  } catch (error) {
    // Keep the dated static snapshot intact when opened offline or while refreshing.
  }
}
refresh();
setInterval(refresh, 60000);
