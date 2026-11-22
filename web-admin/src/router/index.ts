import {
  createRouter,
  createWebHashHistory,
} from "vue-router";

import PersonaView from "../views/PersonaView.vue";
import ConversationsView from "../views/ConversationsView.vue";

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    {
      path: "/",
      redirect: "/persona",
    },
    {
      path: "/persona",
      name: "persona",
      component: PersonaView,
    },
    {
      path: "/conversations",
      name: "conversations",
      component: ConversationsView,
    },
  ],
});

export default router;