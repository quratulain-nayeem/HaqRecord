document.getElementById('login-form').addEventListener('submit', async event => {
  event.preventDefault();
  const button = document.getElementById('sign-in');
  const error = document.getElementById('error');
  button.disabled = true; error.textContent = '';
  try {
    const response = await fetch('/auth/login', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:document.getElementById('username').value,password:document.getElementById('password').value})});
    const data = await response.json();
    if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Check your login details.');
    window.location.assign('/caseworker');
  } catch (problem) {error.textContent = problem.message;}
  finally {button.disabled = false;}
});
