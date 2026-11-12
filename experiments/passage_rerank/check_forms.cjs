// Exercise export/import from the actual HTML, without editing human CSVs.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');

(async () => {
  const directory = process.argv[2];
  if (!directory) throw Error('Pass the experiment output directory');
  const forms = process.argv[3] || path.join(directory, 'reviewers');
  const count = JSON.parse(fs.readFileSync(path.join(directory, 'summary.json'), 'utf8')).unique_pairs;
  const orders = [];
  for (const role of ['A', 'B']) {
    const html = fs.readFileSync(path.join(forms, `reviewer_${role}.html`), 'utf8');
    assert.ok(!html.includes('@@'));
    const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
    const ids = [...html.matchAll(/<section data-pair="(E\d+)"/g)].map(m => m[1]);
    assert.equal(ids.length, count);
    assert.equal(new Set(ids).size, count);
    orders.push(ids);
    const fields = ['grade', 'query_evidence', 'document_evidence', 'reason'];
    const rows = ids.map((id, i) => ({dataset: {pair: id}, cells: Object.fromEntries(fields.map(f =>
      [f, {value: f === 'grade' ? (i === count - 1 ? '' : String(i % 3)) : `${f} tiếng Việt, "quote"\nline two`}])) ,
      querySelector(name) { return this.cells[name.slice(1)]; }}));
    const reviewer = {value: `Thành viên ${role}`}, status = {}, restore = {};
    let blob, filename, clicked = false;
    const alerts = [];
    const context = {
      Blob, setTimeout: fn => fn(), alert: message => alerts.push(message),
      URL: {createObjectURL: value => {blob = value; return 'blob:test';}, revokeObjectURL: () => {}},
      document: {querySelectorAll: () => rows,
        getElementById: id => ({reviewer, status, restore}[id]),
        createElement: () => ({set href(value) {}, set download(value) {filename = value;}, click() {clicked = true;}})}
    };
    vm.runInNewContext(script, context);
    vm.runInNewContext('saveCSV()', context);
    assert.ok(clicked);
    assert.equal(filename, `reviewer_${role}.csv`);
    assert.ok(status.textContent.startsWith(`${count-1}/${count}`));
    const csv = await blob.text();
    const original = rows.map(row => fields.map(f => row.cells[f].value));
    rows.forEach(row => fields.forEach(f => row.cells[f].value = ''));
    reviewer.value = '';
    await restore.onchange({target: {files: [{text: async () => csv}]}});
    assert.deepEqual(rows.map(row => fields.map(f => row.cells[f].value)), original);
    assert.equal(reviewer.value, `Thành viên ${role}`);
    assert.equal(alerts.length, 0);
    await restore.onchange({target: {files: [{text: async () => csv.replace(ids[0], 'WRONG')}]}});
    assert.equal(alerts.pop(), 'Sai danh sách cặp');
    // A grade without evidence must not count as complete.
    rows[0].cells.document_evidence.value = '';
    vm.runInNewContext('saveCSV()', context);
    assert.ok(status.textContent.startsWith(`${count-2}/${count}`));
    console.log(`Form ${role}: ${count} IDs, CSV round trip, Unicode, multiline, pending evidence and wrong-ID rejection passed`);
  }
  assert.deepEqual([...orders[0]].sort(), [...orders[1]].sort());
  assert.notDeepEqual(orders[0], orders[1]);
})().catch(error => {console.error(error); process.exitCode = 1;});
