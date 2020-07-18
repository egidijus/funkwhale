import lodash from '@/lodash'

export function setUpdate(obj, statuses, value) {
  let updatedKeys = lodash.keys(obj)
  updatedKeys.forEach((k) => {
    statuses[k] = value
  })
}

export function parseAPIErrors(responseData, parentField) {
  let errors = []
  for (var field in responseData) {
    if (responseData.hasOwnProperty(field)) {
      let value = responseData[field]
      let fieldName = lodash.startCase(field.replace('_', ' '))
      if (parentField) {
        fieldName = `${parentField} - ${fieldName}`
      }
      if (value.forEach) {
        value.forEach(e => {
          if (e.toLocaleLowerCase().includes('this field ')) {
            errors.push(`${fieldName}: ${e}`)
          } else {
            errors.push(e)
          }
        })
      } else if (typeof value === 'object') {
        // nested errors
        let nestedErrors = parseAPIErrors(value, fieldName)
        errors = [...errors, ...nestedErrors]
      }
    }
  }
  return errors
}

export function getCookie(name) {
  return document.cookie
  .split('; ')
  .find(row => row.startsWith(name))
  .split('=')[1];
}
export function setCsrf(xhr) {
  if (getCookie('csrftoken')) {
    xhr.setRequestHeader('X-CSRFToken', getCookie('csrftoken'))
  }
}

export function checkRedirectToLogin (store, router) {
  console.log('HELLO', store.state.auth.authenticated, router.currentRoute.fullPath)
  if (!store.state.auth.authenticated) {
    router.push({name: 'login', query: {next: router.currentRoute.fullPath}})
  }
}
