import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import DocumentList from '../DocumentList';

// Mock the api module
vi.mock('../../services/api', () => ({
  default: {
    get: vi.fn(),
    delete: vi.fn(),
  },
}));

import api from '../../services/api';

const wrapper = ({ children }: { children: React.ReactNode }) => {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
};

describe('DocumentList', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows loading state initially', () => {
    (api.get as any).mockReturnValue(new Promise(() => {})); // never resolves
    render(<DocumentList />, { wrapper });
    // The Loader2 icon renders an SVG with the animate-spin class
    expect(document.querySelector('.animate-spin, svg')).toBeTruthy();
  });

  it('shows empty state when no documents', async () => {
    (api.get as any).mockResolvedValue({ data: { documents: [] } });
    render(<DocumentList />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('No documents yet')).toBeInTheDocument();
    });
  });

  it('renders document cards when data is returned', async () => {
    (api.get as any).mockResolvedValue({
      data: {
        documents: [
          { doc_id: '1', filename: 'report.pdf', chunk_count: 12, status: 'completed', created_at: '2024-01-01' },
          { doc_id: '2', filename: 'notes.docx', chunk_count: 5, status: 'completed', created_at: '2024-01-02' },
        ],
      },
    });

    render(<DocumentList />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('report.pdf')).toBeInTheDocument();
      expect(screen.getByText('notes.docx')).toBeInTheDocument();
    });
  });

  it('shows chunk count for each document', async () => {
    (api.get as any).mockResolvedValue({
      data: {
        documents: [
          { doc_id: '1', filename: 'test.pdf', chunk_count: 8, status: 'completed', created_at: '2024-01-01' },
        ],
      },
    });

    render(<DocumentList />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText(/8 chunks/)).toBeInTheDocument();
    });
  });

  it('calls delete API when delete button is clicked and confirmed', async () => {
    (api.get as any).mockResolvedValue({
      data: {
        documents: [
          { doc_id: 'doc-1', filename: 'delete_me.pdf', chunk_count: 3, status: 'completed', created_at: '2024-01-01' },
        ],
      },
    });
    (api.delete as any).mockResolvedValue({});

    // Mock window.confirm
    vi.spyOn(window, 'confirm').mockReturnValue(true);

    render(<DocumentList />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('delete_me.pdf')).toBeInTheDocument();
    });

    const deleteBtn = screen.getByTitle('Delete document');
    fireEvent.click(deleteBtn);

    await waitFor(() => {
      expect(api.delete).toHaveBeenCalledWith('/documents/doc-1');
    });
  });
});
