import { LitElement, html, css } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { subscribeAuth, signOut, User } from '../services/auth';

@customElement('auth-avatar')
export class AuthAvatar extends LitElement {
  @state() initialized: boolean = false;
  @state() user: User | null = null;

  _unsubscribe?: () => void;

  connectedCallback() {
    super.connectedCallback();
    this._unsubscribe = subscribeAuth(async (user) => {
      this.user = user;
      this.initialized = true;
    });
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this._unsubscribe?.();
  }

  createRenderRoot() {
    return this; // Disable shadow DOM
  }

  async handleLogout() {
    localStorage.removeItem('photoUrl');
    await signOut();
  }

  async handleSelect(e: CustomEvent) {
    let value = e.detail.item.value;
    if (value === 'logout') {
      await this.handleLogout();
    }
  }

  render() {
    let photoUrl = localStorage.getItem('photoUrl')
    if (this.user) {
      let photoURL = photoUrl || this.user.photoURL || 'https://via.placeholder.com/40';
      let name = this.user.displayName || 'User';
      localStorage.setItem('photoUrl', this.user.photoURL || '');
      return html`
        <wa-dropdown>
          <wa-avatar slot="trigger" name=${name} image=${photoURL}></wa-avatar>
          <wa-menu @wa-select=${this.handleSelect}>
            <wa-menu-label>${name}<br/>${this.user.email}</wa-menu-label>
            <wa-menu-item value="logout">Logout</wa-menu-item>
          </wa-menu>
        </wa-dropdown>
          `;
    } else if (!this.initialized && photoUrl) {
      return html`<wa-avatar name="Loading" image=${photoUrl}></wa-avatar>`;
    } else {
      return html`<a class="text button" href="/auth">Login</a>`;
    }
  }
}