/**
 * Session bootstrap coordination.
 *
 * `AppProviders` restores the session from the refresh cookie and resolves this
 * promise; the router awaits it before deciding whether to redirect to /login,
 * so a page reload never flashes the login screen.
 */

let resolveBootstrap: (() => void) | null = null

const promise = new Promise<void>((resolve) => {
  resolveBootstrap = resolve
})

export const sessionBootstrap = {
  promise,
  complete: () => {
    resolveBootstrap?.()
    resolveBootstrap = null
  },
}
