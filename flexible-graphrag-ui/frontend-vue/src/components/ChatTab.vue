<template>
  <div class="pa-4 d-flex flex-column" style="height: calc(100vh - 200px);">
    <!-- Header -->
    <div class="d-flex justify-space-between align-center mb-4">
      <h2>Chat Interface</h2>
      <div class="d-flex align-center ga-2">
        <v-chip
          prepend-icon="mdi-chat-question"
          color="primary"
          variant="outlined"
        >
          Q&A Mode
        </v-chip>
        <v-btn
          variant="outlined"
          size="small"
          :disabled="chatMessages.length === 0"
          @click="clearChatHistory"
        >
          CLEAR HISTORY
        </v-btn>
      </div>
    </div>

    <!-- Chat Messages -->
    <v-card
      ref="chatContainer"
      class="flex-grow-1 pa-4 mb-4 overflow-y-auto"
      color="grey-lighten-5"
      variant="outlined"
    >
      <!-- Welcome Message -->
      <div
        v-if="chatMessages.length === 0"
        class="d-flex flex-column align-center justify-center h-100 text-medium-emphasis"
      >
        <v-avatar size="48" class="mb-4" color="grey-lighten-3">
          <img :src="agentIcon" alt="Assistant" style="width: 32px; height: 32px; border-radius: 50%;" />
        </v-avatar>
        <h3 class="mb-2">Welcome to Flexible GraphRAG Chat</h3>
        <p class="text-center">
          Ask questions about your documents and get conversational answers.
          <br />
          The AI will provide detailed responses based on your processed documents.
        </p>
      </div>

      <!-- Chat Messages List -->
      <div v-else>
        <div
          v-for="(message, index) in chatMessages"
          :key="message.id"
          class="mb-4"
        >
          <div
            :class="[
              'd-flex align-start',
              message.type === 'user' ? 'flex-row-reverse' : 'flex-row'
            ]"
          >
            <!-- Avatar -->
            <v-avatar
              :color="message.type === 'user' ? 'primary' : 'success'"
              size="32"
              class="mx-2"
            >
              <v-icon v-if="message.type === 'user'" color="white">mdi-account</v-icon>
              <img v-else :src="agentIcon" alt="Assistant" style="width: 24px; height: 24px; border-radius: 50%;" />
            </v-avatar>

            <!-- Message Content -->
            <v-card
              :class="[
                'pa-3',
                message.type === 'user' ? 'bg-blue-lighten-5' : 'bg-white'
              ]"
              :style="{ 
                maxWidth: message.type === 'user' ? '70%' : '80%',
                color: '#000000'
              }"
              variant="outlined"
            >
              <!-- Loading State -->
              <div v-if="message.isLoading" class="d-flex align-center ga-2">
                <v-progress-circular
                  indeterminate
                  size="16"
                  width="2"
                  color="primary"
                ></v-progress-circular>
                <span class="text-caption text-medium-emphasis">Thinking...</span>
              </div>

              <!-- Message Content -->
              <div v-else>
                <p class="mb-2">{{ message.content }}</p>
                <div class="text-caption" style="color: #333333; font-weight: 500;">
                  {{ formatTime(message.timestamp) }}
                </div>
              </div>
            </v-card>
          </div>

          <!-- Divider -->
          <v-divider v-if="index < chatMessages.length - 1" class="my-2"></v-divider>
        </div>
      </div>
    </v-card>

    <!-- Input Area -->
    <div class="d-flex align-end ga-2">
      <v-textarea
        v-model="chatInput"
        placeholder="Ask a question... (e.g., 'What are the key findings about AI?')"
        variant="outlined"
        rows="1"
        auto-grow
        max-rows="3"
        :disabled="isQuerying"
        @keydown.enter.exact.prevent="handleChatSubmit"
        @keydown.enter.shift.exact="() => {}"
        class="flex-grow-1"
      ></v-textarea>
      
      <v-btn
        icon
        color="primary"
        size="large"
        :disabled="!chatInput.trim() || isQuerying"
        :loading="isQuerying"
        @click="handleChatSubmit"
        style="width: 48px; height: 48px;"
      >
        <v-icon>mdi-send</v-icon>
      </v-btn>
    </div>

    <!-- Help Text -->
    <p class="text-caption text-medium-emphasis text-center mt-2">
      Press Enter to send, Shift+Enter for new line • 
      Q&A mode: Provides conversational answers
    </p>

    <!-- Error Message -->
    <v-alert
      v-if="error"
      type="error"
      class="mt-4"
      closable
      @click:close="error = ''"
    >
      {{ error }}
    </v-alert>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, nextTick, watch } from 'vue';
import axios from 'axios';
import agentIcon from '../assets/agent.png';

interface ChatMessage {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  queryType?: 'search' | 'qa';
  results?: any[];
  isLoading?: boolean;
}

interface QueryRequest {
  query: string;
  query_type?: string;
  top_k?: number;
}

interface ApiResponse {
  success?: boolean;
  status?: string;
  message?: string;
  error?: string;
  answer?: string;
  results?: any[];
}

export default defineComponent({
  name: 'ChatTab',
  setup() {
    // State
    const chatMessages = ref<ChatMessage[]>([]);
    const chatInput = ref('');
    const isQuerying = ref(false);
    const error = ref('');
    const chatContainer = ref<HTMLElement>();

    // Methods
    const formatTime = (timestamp: Date): string => {
      return timestamp.toLocaleTimeString();
    };

    const scrollToBottom = async () => {
      await nextTick();
      if (chatContainer.value) {
        const element = chatContainer.value.$el || chatContainer.value;
        setTimeout(() => {
          element.scrollTop = element.scrollHeight;
        }, 0);
      }
    };

    const handleChatSubmit = async () => {
      if (!chatInput.value.trim() || isQuerying.value) return;
      
      const userMessage: ChatMessage = {
        id: Date.now().toString(),
        type: 'user',
        content: chatInput.value.trim(),
        timestamp: new Date(),
        queryType: 'qa'
      };
      
      // Add user message
      chatMessages.value.push(userMessage);
      
      // Add loading assistant message
      const loadingMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: '',
        timestamp: new Date(),
        queryType: 'qa',
        isLoading: true
      };
      chatMessages.value.push(loadingMessage);
      
      const currentInput = chatInput.value;
      chatInput.value = '';
      
      await scrollToBottom();
      
      try {
        isQuerying.value = true;
        error.value = '';
        
        const request: QueryRequest = {
          query: currentInput,
          query_type: 'qa',
          top_k: 10
        };
        
        const response = await axios.post<ApiResponse>('/api/search', request);
        
        // Remove loading message
        const messageIndex = chatMessages.value.findIndex(msg => msg.id === loadingMessage.id);
        if (messageIndex !== -1) {
          chatMessages.value.splice(messageIndex, 1);
        }
        
        if (response.data.success) {
          const assistantMessage: ChatMessage = {
            id: (Date.now() + 2).toString(),
            type: 'assistant',
            content: response.data.answer || 'No answer provided',
            timestamp: new Date(),
            queryType: 'qa'
          };
          chatMessages.value.push(assistantMessage);
        } else {
          const errorMessage: ChatMessage = {
            id: (Date.now() + 2).toString(),
            type: 'assistant',
            content: `Error: ${response.data.error || 'Unknown error occurred'}`,
            timestamp: new Date(),
            queryType: 'qa'
          };
          chatMessages.value.push(errorMessage);
        }
      } catch (err) {
        console.error('Error in chat query:', err);
        const errorMessage = axios.isAxiosError(err)
          ? err.response?.data?.detail || err.response?.data?.error || 'Error executing query'
          : 'An unknown error occurred';
        
        // Remove loading message
        const messageIndex = chatMessages.value.findIndex(msg => msg.id === loadingMessage.id);
        if (messageIndex !== -1) {
          chatMessages.value.splice(messageIndex, 1);
        }
        
        const errorMsg: ChatMessage = {
          id: (Date.now() + 2).toString(),
          type: 'assistant',
          content: `Error: ${errorMessage}`,
          timestamp: new Date(),
          queryType: 'qa'
        };
        chatMessages.value.push(errorMsg);
      } finally {
        isQuerying.value = false;
        await scrollToBottom();
      }
    };

    const clearChatHistory = () => {
      chatMessages.value = [];
    };

    // Auto-scroll when messages change
    watch(chatMessages, scrollToBottom, { deep: true });

    return {
      chatMessages,
      chatInput,
      isQuerying,
      error,
      chatContainer,
      agentIcon,
      formatTime,
      handleChatSubmit,
      clearChatHistory,
    };
  },
});
</script>

<style scoped>
.h-100 {
  height: 100%;
}

.overflow-y-auto {
  overflow-y: auto;
}

.flex-grow-1 {
  flex-grow: 1;
}
</style>
