<template>
  <v-app>
    <v-app-bar app color="primary" dark>
      <v-toolbar-title>Flexible GraphRAG (Vue)</v-toolbar-title>
    </v-app-bar>

    <v-main>
      <v-container class="py-8">
        <process-folder @processed="onFolderProcessed" />
        <query-form />
      </v-container>
    </v-main>
  </v-app>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import ProcessFolder from './components/ProcessFolder.vue';
import QueryForm from './components/QueryForm.vue';

export default defineComponent({
  name: 'App',
  components: {
    ProcessFolder,
    QueryForm,
  },
  methods: {
    onFolderProcessed(event: { dataSource: string, path?: string }) {
      console.log('Documents processed:', event);
      // You can add any additional logic here when documents are processed
    }
  }
});
</script>

<style>
@import 'https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap';
</style>