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

// Turn a FastAPI error body's `detail` into a readable string. `detail` may be
// a plain string (e.g. "Account already exists") or, for 422 validation
// errors, an array of {loc, msg, type} objects — rendering the latter directly
// yields the useless "[object Object]".
const formatDetail = (detail, status) => {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail.map((e) => e.msg || JSON.stringify(e)).join('; ')
  }
  if (detail) return JSON.stringify(detail)
  return String(status)
}

// Show a Bootstrap toast in a top-right container (created on first use), so
// background actions can report their result without navigating away or
// blocking on alert(). `variant` is a Bootstrap colour (success/danger/…).
const showToast = (message, variant = 'primary') => {
  let container = document.getElementById('toast-container')
  if (!container) {
    container = document.createElement('div')
    container.id = 'toast-container'
    container.className = 'toast-container position-fixed top-0 end-0 p-3'
    container.style.zIndex = '1100'
    document.body.appendChild(container)
  }
  const toast = document.createElement('div')
  toast.className = `toast align-items-center text-bg-${variant} border-0`
  toast.setAttribute('role', 'alert')
  const body = document.createElement('div')
  body.className = 'toast-body'
  body.textContent = message // textContent: never interpolate server data as HTML
  const close = document.createElement('button')
  close.type = 'button'
  close.className = 'btn-close btn-close-white me-2 m-auto'
  close.setAttribute('data-bs-dismiss', 'toast')
  close.setAttribute('aria-label', 'Close')
  const row = document.createElement('div')
  row.className = 'd-flex'
  row.append(body, close)
  toast.append(row)
  container.appendChild(toast)
  if (window.bootstrap) {
    const t = bootstrap.Toast.getOrCreateInstance(toast, { delay: 5000 })
    toast.addEventListener('hidden.bs.toast', () => toast.remove())
    t.show()
  } else {
    // Bootstrap JS missing — fall back so the message is never lost.
    alert(message)
    toast.remove()
  }
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
      alert('Update failed: ' + formatDetail(err.detail, response.status))
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
      alert('Delete failed: ' + formatDetail(err.detail, response.status))
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
      alert('Photo upload failed: ' + formatDetail(err.detail, response.status))
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
      alert('Photo delete failed: ' + formatDetail(err.detail, response.status))
    }
  })
}

// handle signup form by sending JSON, matching server expectations
const signupForm = document.getElementById('signup-form')
if (signupForm) {
  signupForm.addEventListener('submit', async (e) => {
    e.preventDefault()

    // The single "username" field holds the user's email address (see the
    // form: type="email", placeholder name@example.com). UserModel requires a
    // separate `email`, so mirror it here — matching the server's form branch.
    const payload = {
      username: signupForm.username.value,
      email: signupForm.username.value,
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
      const err = await response.json().catch(() => ({}))
      alert('Registration failed: ' + formatDetail(err.detail, response.status))
    }
  })
}

// --- "Insert fake data" button (admin only). Seeds the DB via fetch and
// reports the outcome in a toast instead of navigating to the raw JSON. When
// the server reports data already exists it offers a wipe-and-reseed.
const seedBtn = document.getElementById('insertFakeDataButton')
if (seedBtn) {
  const runSeed = async (reset = false) => {
    // POST because seeding mutates (and reset destroys) data; the trailing
    // slash avoids a redirect and the session cookie authorises us.
    let response
    try {
      response = await fetch(reset ? '/seed/?reset=true' : '/seed/', { method: 'POST' })
    } catch (e) {
      showToast('Seed request failed: ' + e.message, 'danger')
      return
    }
    if (response.status === 401) {
      showToast('Log in as an admin to seed demo data.', 'warning')
      return
    }
    if (response.status === 403) {
      showToast('Seeding demo data is allowed for admins only.', 'warning')
      return
    }
    const data = await response.json().catch(() => ({}))
    if (!response.ok) {
      showToast('Seed failed: ' + formatDetail(data.detail, response.status), 'danger')
      return
    }
    if (data.status === 'skipped') {
      if (confirm(`Database already has ${data.students} students. Wipe and reseed from scratch?`)) {
        await runSeed(true)
      } else {
        showToast('Seeding skipped — data already exists.', 'secondary')
      }
      return
    }
    const summary = Object.entries(data.counts || {})
      .map(([entity, n]) => `${n} ${entity}`)
      .join(', ')
    showToast(`Data ${data.status}: ${summary}.`, 'success')
  }

  seedBtn.addEventListener('click', () => {
    // Close the confirmation modal cleanly, then seed in the background.
    const modalEl = document.getElementById('modal-info')
    if (modalEl && window.bootstrap) {
      bootstrap.Modal.getOrCreateInstance(modalEl).hide()
    }
    runSeed(false)
  })
}
