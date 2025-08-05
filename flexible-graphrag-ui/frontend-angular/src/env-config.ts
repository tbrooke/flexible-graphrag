/**
 * This script loads environment variables from the .env file
 * and makes them available to the Angular app via window.__env
 */

// Define the environment interface
interface Environment {
  DEFAULT_FOLDER_PATH: string;
}

// Declare the __env property on the window object
declare global {
  interface Window {
    __env: Environment;
  }
}

// Initialize the environment
window.__env = window.__env || {
  // Default value that will be overridden by the server
  DEFAULT_FOLDER_PATH: '/Shared/GraphRAG'
};

// The server will inject actual values from .env here
// DO NOT MODIFY THIS COMMENT: ENV_INJECTION_POINT

export {}; // This file needs to be a module
