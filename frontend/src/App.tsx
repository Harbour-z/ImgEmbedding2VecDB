import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { HomePage } from './pages/HomePage';
import { ChatPage } from './pages/ChatPage';
import { GalleryPage } from './pages/GalleryPage';
import { UploadPage } from './pages/UploadPage';
import { ArchitecturePage } from './pages/ArchitecturePage';
import { MarkdownTestPage } from './pages/MarkdownTestPage';
import { ConversationListPage } from './pages/ConversationListPage';
import MainLayout from './components/layout/MainLayout';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<HomePage />} />
          <Route path="chat" element={<ChatPage />} />
          <Route path="conversations" element={<ConversationListPage />} />
          <Route path="gallery" element={<GalleryPage />} />
          <Route path="upload" element={<UploadPage />} />
          <Route path="architecture" element={<ArchitecturePage />} />
          <Route path="markdown-test" element={<MarkdownTestPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
