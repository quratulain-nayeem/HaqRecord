let csrf = '';
async function initialize() {
  const response = await fetch('/auth/session');
  if (!response.ok) {window.location.replace('/login');return;}
  const session = await response.json();
  csrf = session.csrf_token;
  document.getElementById('who').textContent = session.username;
}
document.getElementById('logout').addEventListener('click', async () => {
  const response = await fetch('/auth/logout', {method:'POST',headers:{'X-CSRF-Token':csrf}});
  if (response.ok || response.status === 401) window.location.replace('/login');
  else document.getElementById('error').textContent = 'Unable to sign out. Refresh the page and try again.';
});
document.getElementById('lookup').addEventListener('submit', async event => {
  event.preventDefault();
  const output = document.getElementById('record');
  const error = document.getElementById('error');
  error.textContent='';output.hidden=true;output.textContent='';
  try {
    const reference = document.getElementById('reference').value.trim();
    const response = await fetch('/cases/' + encodeURIComponent(reference));
    if (response.status === 401) {window.location.replace('/login');return;}
    if (!response.ok) throw new Error('Case not found. Check the reference.');
    output.textContent = JSON.stringify(await response.json(), null, 2);
    output.hidden=false;
  } catch (problem) {error.textContent=problem.message;}
});
initialize().catch(() => {document.getElementById('error').textContent='Unable to check your session. Refresh to retry.';});
