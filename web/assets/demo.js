const $ = id => document.getElementById(id);
let current = null;
async function calculate(event) {
  if (event) event.preventDefault();
  $('demo-error').textContent = '';
  $('payment').disabled = true;
  current = null;
  try {
    const response = await fetch('/calculate', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({days_worked:Number($('days').value),daily_rate:$('rate').value,payments_received:$('paid').value})});
    if (!response.ok) throw new Error('Enter valid days and amounts, with at most two decimal places.');
    current = await response.json();
    $('balance').textContent = '₹' + current.balance;
    $('arithmetic').textContent = current.calculation;
    $('payment').disabled = false;
  } catch(error) {$('demo-error').textContent = error.message;}
}
$('demo-form').addEventListener('submit', event => {$('history').textContent='';calculate(event);});
for (const id of ['days','rate','paid']) $(id).addEventListener('input', () => {current=null;$('payment').disabled=true;$('balance').textContent='—';$('arithmetic').textContent='Calculate again to update the balance.';$('history').textContent='';});
$('payment').addEventListener('click', async () => {
  if (!current) return;
  const previous = current.balance;
  const cents = Math.round(Number(current.payments_received) * 100) + 100000;
  $('paid').value = (cents / 100).toFixed(2);
  await calculate();
  if (current) $('history').textContent = `Fictional update: ₹${previous} − ₹1,000.00 = ₹${current.balance}. Nothing was saved.`;
});
$('reset').addEventListener('click', () => {$('days').value=8;$('rate').value=800;$('paid').value=2500;$('history').textContent='';calculate();});
calculate();
