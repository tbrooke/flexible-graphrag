# CMIS GraphRAG - Angular Frontend

This is the Angular frontend for the CMIS GraphRAG application.

## Prerequisites

- Node.js (v18 or later)
- npm (v9 or later) or yarn
- Angular CLI (v20 or later)

## Setup

1. Install dependencies:
   ```bash
   npm install
   ```

2. Start the development server:
   ```bash
   ng serve
   ```

3. Open your browser and navigate to `http://localhost:4200/`

## Project Structure

- `src/app/components` - Reusable components
  - `process-folder` - Component for processing folders
  - `query-form` - Component for querying the knowledge graph
- `src/app/services` - Services for API communication
- `src/app/models` - TypeScript interfaces for API requests/responses
- `src/app/shared` - Shared modules and utilities

## Build

Run `ng build` to build the project. The build artifacts will be stored in the `dist/` directory.
