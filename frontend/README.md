# React Frontend Setup

This directory will contain the React (TypeScript) frontend for the Local AI Developer Agent.

## Recommended Setup (using Vite):

1.  Navigate to this `frontend` directory in your terminal:
    ```bash
    cd frontend
    ```

2.  Create a new React TypeScript project using Vite (recommended for speed and modern setup):
    ```bash
    npm create vite@latest .
    # or
    # yarn create vite .
    ```
    When prompted:
    *   Select `react` as the framework.
    *   Select `react-ts` (React with TypeScript) as the variant.

3.  Install dependencies:
    ```bash
    npm install
    # or
    # yarn install
    ```

4.  You will also need an HTTP client like `axios`:
    ```bash
    npm install axios
    # or
    # yarn add axios
    ```

## Alternative Setup (using Create React App):

1.  If you prefer Create React App, navigate to the parent directory (where `agent.py` is) and run:
    ```bash
    npx create-react-app frontend --template typescript
    ```
    Then `cd frontend` and install `axios`.

## Next Steps:

*   Develop React components to interact with the Python FastAPI backend (running on `http://localhost:8000` by default).
*   Implement UI for:
    *   API Key Configuration
    *   Project Loading
    *   File Tree Display
    *   Code Editor
    *   Chat Interface
    *   Displaying and Applying AI Suggestions
