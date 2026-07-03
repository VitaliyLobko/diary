// handle login form via fetch so that we can process JSON response
const loginForm = document.getElementById('login-form')
if (loginForm) {
  loginForm.addEventListener('submit', async (e) => {
    e.preventDefault()
    const data = new URLSearchParams({
      username: loginForm.username.value,
      password: loginForm.password.value,
    })

    const response = await fetch('http://localhost:8000/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: data,
    })
    console.log(response.status, response.statusText)
    if (response.status === 200) {
      const result = await response.json()
      localStorage.setItem('accessToken', result.access_token)
      window.location = '/students'
    }
  })
}

// handle signup form by sending JSON, matching server expectations
const signupForm = document.getElementById('signup-form')
if (signupForm) {
  signupForm.addEventListener('submit', async (e) => {
    e.preventDefault()

    const payload = {
      username: signupForm.username.value,
      password: signupForm.password.value,
    }

    const response = await fetch('http://localhost:8000/signup', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    })

    console.log(response.status, response.statusText)
    if (response.status === 201) {
      // registration succeeded; you might redirect to login or show a message
      window.location = '/'
    } else {
      const err = await response.json()
      alert(err.detail || 'Registration failed')
    }
  })
}
