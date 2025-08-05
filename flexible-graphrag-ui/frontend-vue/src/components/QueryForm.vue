<template>
  <v-card class="pa-4">
    <v-card-title>Ask a Question</v-card-title>
    <v-card-text>
      <v-text-field
        v-model="question"
        label="Ask a question"
        variant="outlined"
        @keyup.enter="handleQuery"
        :loading="isQuerying"
        :disabled="isQuerying"
        class="mb-4"
        @keydown.enter.prevent
      ></v-text-field>
      <v-btn
        color="primary"
        @click="handleQuery"
        :disabled="!question.trim() || isQuerying"
        :loading="isQuerying"
      >
        {{ isQuerying ? '' : 'Ask' }}
        <template v-slot:loader>
          <v-progress-circular indeterminate size="24"></v-progress-circular>
        </template>
      </v-btn>

      <v-alert
        v-if="answer"
        type="info"
        class="mt-4"
      >
        <strong>Answer:</strong> {{ formattedAnswer }}
      </v-alert>

      <v-alert
        v-if="error"
        type="error"
        class="mt-4"
      >
        {{ error }}
      </v-alert>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import axios from 'axios';
import type { QueryRequest, ApiResponse } from '../types/api';

const question = ref('');
const isQuerying = ref(false);
const error = ref('');
const answer = ref('');

const formattedAnswer = computed(() => {
  return answer.value;
});

const handleQuery = async (): Promise<void> => {
  if (!question.value.trim()) return;
  
  try {
    isQuerying.value = true;
    error.value = '';
    
    const response = await axios.post<ApiResponse>(
      '/api/query',
      { question: question.value } as QueryRequest
    );
    
    // Handle simplified response structure
    if (response.data.answer) {
      answer.value = response.data.answer;
    } else {
      answer.value = 'No answer found';
    }
  } catch (err: any) {
    console.error('Error querying:', err);
    error.value = err.response?.data?.detail || 'Error executing query';
  } finally {
    isQuerying.value = false;
  }
};
</script>