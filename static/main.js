// The login form submits natively to POST /login/web, which sets an HttpOnly
// session cookie and redirects to the home page. No JS interception needed —
// a fetch + localStorage token is invisible to server-rendered pages.

// --- Generic detail-page Edit (PUT) / Delete (DELETE), shared by the student,
// teacher and any future entity card. The request target is simply the current
// URL (e.g. /teachers/10), and the payload is built from the form's named
// inputs. The session cookie is sent automatically for same-origin requests,
// so admins/moderators are authorised transparently.
const coerce = (v) => {
  if (v === 'true') return true
  if (v === 'false') return false
  if (/^\d+$/.test(v)) return Number(v)
  return v
}

const saveDetailBtn = document.getElementById('save-detail-btn')
if (saveDetailBtn) {
  saveDetailBtn.addEventListener('click', async () => {
    const form = document.getElementById('edit-detail-form')
    const payload = {}
    form.querySelectorAll('[name]').forEach((el) => {
      payload[el.name] = coerce(el.value)
    })
    const response = await fetch(window.location.pathname, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (response.ok) {
      // Close the edit modal cleanly (removes the backdrop), then reload so
      // the freshly saved data is rendered by the server.
      const modalEl = document.getElementById('modal-edit')
      if (modalEl && window.bootstrap) {
        bootstrap.Modal.getOrCreateInstance(modalEl).hide()
      }
      window.location.reload()
    } else {
      const err = await response.json().catch(() => ({}))
      alert('Update failed: ' + (err.detail ? JSON.stringify(err.detail) : response.status))
    }
  })
}

const deleteDetailBtn = document.getElementById('delete-detail-btn')
if (deleteDetailBtn) {
  deleteDetailBtn.addEventListener('click', async () => {
    const response = await fetch(window.location.pathname, { method: 'DELETE' })
    if (response.status === 204) {
      // /students/1 -> /students , /teachers/10 -> /teachers
      window.location = window.location.pathname.replace(/\/[^/]+\/?$/, '')
    } else {
      const err = await response.json().catch(() => ({}))
      alert('Delete failed: ' + (err.detail ? JSON.stringify(err.detail) : response.status))
    }
  })
}

// --- Detail-page photo: click the image (or "Change photo") to upload, and
// "Delete photo" to remove it. Target is the current URL + "/photo".
const photoInput = document.getElementById('photo-input')
if (photoInput) {
  const openPicker = () => photoInput.click()
  const photoImg = document.getElementById('detail-photo')
  const uploadBtn = document.getElementById('upload-photo-btn')
  if (photoImg) photoImg.addEventListener('click', openPicker)
  if (uploadBtn) uploadBtn.addEventListener('click', openPicker)

  photoInput.addEventListener('change', async () => {
    if (!photoInput.files.length) return
    const formData = new FormData()
    formData.append('file', photoInput.files[0])
    const response = await fetch(window.location.pathname + '/photo', {
      method: 'POST',
      body: formData,
    })
    if (response.ok) {
      window.location.reload()
    } else {
      const err = await response.json().catch(() => ({}))
      alert('Photo upload failed: ' + (err.detail ? JSON.stringify(err.detail) : response.status))
    }
  })
}

const deletePhotoBtn = document.getElementById('delete-photo-btn')
if (deletePhotoBtn) {
  deletePhotoBtn.addEventListener('click', async () => {
    const response = await fetch(window.location.pathname + '/photo', { method: 'DELETE' })
    if (response.ok) {
      window.location.reload()
    } else {
      const err = await response.json().catch(() => ({}))
      alert('Photo delete failed: ' + (err.detail ? JSON.stringify(err.detail) : response.status))
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
