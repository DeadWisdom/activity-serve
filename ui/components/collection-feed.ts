import { LitElement, html, css } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { subscribeAuth, User } from '../services/auth';
import { getCollection, getMe, getOutbox } from '../services/api';

@customElement('collection-feed')
export class CollectionFeed extends LitElement {
  @state() initialized: boolean = false;
  @state() user: User | null = null;
  @state() collection?: any;

  _unsubscribe?: () => void;

  connectedCallback() {
    super.connectedCallback();
    this._unsubscribe = subscribeAuth(async (user) => {
      this.user = user;
      this.initialized = true;
      this.sync();
    });
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this._unsubscribe?.();
  }

  async sync() {
    let me = await getMe();
    if (me) {
      this.collection = await getOutbox();
    }
  }

  renderItem(item: any) {
    return html`<code class="json">${JSON.stringify(item, null, 2)}</code>`;
  }

  render() {
    if (!this.collection) return;

    return html`
      <h3>${this.collection.summary}</h3>
      ${this.collection.items.map((item: any) => this.renderItem(item))}
    `;
  }
}