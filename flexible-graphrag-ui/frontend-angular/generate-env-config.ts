/**
 * Script to generate env-config.json from .env file
 * Run with: npx ts-node generate-env-config.ts
 */
import * as fs from 'fs';
import * as path from 'path';
import * as dotenv from 'dotenv';
import { fileURLToPath } from 'url';

// Get directory name in ES modules
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Load .env file
const envFilePath = path.resolve(__dirname, '.env');
const envSamplePath = path.resolve(__dirname, 'dot-env-sample.txt');
const outputPath = path.resolve(__dirname, 'src/assets/env-config.json');

// Default configuration
const defaultConfig = {
  DEFAULT_FOLDER_PATH: '/Shared/GraphRAG'
};

// Create output directory if it doesn't exist
const outputDir = path.dirname(outputPath);
if (!fs.existsSync(outputDir)) {
  fs.mkdirSync(outputDir, { recursive: true });
}

try {
  // Try to load .env file
  if (fs.existsSync(envFilePath)) {
    console.log(`Loading environment from ${envFilePath}`);
    const envConfig = dotenv.parse(fs.readFileSync(envFilePath));
    
    // Create config object with values from .env
    const config = {
      ...defaultConfig,
      ...envConfig
    };
    
    // Write to output file
    fs.writeFileSync(outputPath, JSON.stringify(config, null, 2));
    console.log(`Environment configuration written to ${outputPath}`);
  } else {
    // If .env doesn't exist, use sample or defaults
    console.log(`.env file not found at ${envFilePath}`);
    
    if (fs.existsSync(envSamplePath)) {
      console.log(`Using sample from ${envSamplePath}`);
      const sampleConfig = dotenv.parse(fs.readFileSync(envSamplePath));
      
      const config = {
        ...defaultConfig,
        ...sampleConfig
      };
      
      fs.writeFileSync(outputPath, JSON.stringify(config, null, 2));
      console.log(`Environment configuration written to ${outputPath}`);
    } else {
      // Use defaults
      console.log(`Using default configuration`);
      fs.writeFileSync(outputPath, JSON.stringify(defaultConfig, null, 2));
      console.log(`Default configuration written to ${outputPath}`);
    }
  }
} catch (error) {
  console.error('Error generating environment configuration:', error);
  
  // Write defaults on error
  fs.writeFileSync(outputPath, JSON.stringify(defaultConfig, null, 2));
  console.log(`Default configuration written to ${outputPath} due to error`);
}
