<template>
  <v-app>
    <v-app-bar app color="primary" dark>
      <v-toolbar-title>Flexible GraphRAG (Vue)</v-toolbar-title>
    </v-app-bar>

    <v-main>
      <v-container class="py-8" fluid>
        <v-card elevation="3">
          <v-tabs 
            v-model="mainTab" 
            grow 
            color="primary"
            bg-color="grey-lighten-4"
            slider-color="primary"
            class="custom-tabs">
            <v-tab value="sources">SOURCES</v-tab>
            <v-tab value="processing">PROCESSING</v-tab>
            <v-tab value="search">SEARCH</v-tab>
            <v-tab value="chat">CHAT</v-tab>
            <!-- <v-tab value="graph">Graph</v-tab> -->
          </v-tabs>

          <v-card-text>
            <v-window v-model="mainTab">
              <!-- Sources Tab -->
              <v-window-item value="sources">
                <sources-tab 
                  @configure-processing="onConfigureProcessing"
                  @sources-configured="onSourcesConfigured"
                />
              </v-window-item>

              <!-- Processing Tab -->
              <v-window-item value="processing">
                <processing-tab 
                  :has-configured-sources="hasConfiguredSources"
                  :configured-data-source="configuredDataSource"
                  :configured-files="configuredFiles"
                  @go-to-sources="mainTab = 'sources'"
                  @files-removed="configuredFiles = $event"
                />
              </v-window-item>

              <!-- Search Tab -->
              <v-window-item value="search">
                <search-tab />
              </v-window-item>

              <!-- Chat Tab -->
              <v-window-item value="chat">
                <chat-tab />
              </v-window-item>

              <!-- Graph Tab (hidden for now) -->
              <!-- <v-window-item value="graph">
                <graph-tab />
              </v-window-item> -->
            </v-window>
          </v-card-text>
        </v-card>
      </v-container>
    </v-main>
  </v-app>
</template>

<script lang="ts">
import { defineComponent, ref } from 'vue';
import SourcesTab from './components/SourcesTab.vue';
import ProcessingTab from './components/ProcessingTab.vue';
import SearchTab from './components/SearchTab.vue';
import ChatTab from './components/ChatTab.vue';

export default defineComponent({
  name: 'App',
  components: {
    SourcesTab,
    ProcessingTab,
    SearchTab,
    ChatTab,
  },
  setup() {
    const mainTab = ref('sources');
    const hasConfiguredSources = ref(false);
    const configuredDataSource = ref('');
    const configuredFiles = ref<File[]>([]);

    const onConfigureProcessing = () => {
      mainTab.value = 'processing';
    };

    const onSourcesConfigured = (data: { dataSource: string; files: File[] }) => {
      hasConfiguredSources.value = true;
      configuredDataSource.value = data.dataSource;
      configuredFiles.value = data.files;
    };

    return {
      mainTab,
      hasConfiguredSources,
      configuredDataSource,
      configuredFiles,
      onConfigureProcessing,
      onSourcesConfigured,
    };
  },
});
</script>

<style>
@import 'https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap';

.custom-tabs {
  border-bottom: 1px solid #e0e0e0;
}

.custom-tabs .v-tab {
  font-weight: 500;
  text-transform: none;
  letter-spacing: 0.5px;
}

.custom-tabs .v-tab--selected {
  background-color: #1976d2;
  color: white !important;
}

.custom-tabs .v-tabs-slider {
  height: 3px;
}
</style>