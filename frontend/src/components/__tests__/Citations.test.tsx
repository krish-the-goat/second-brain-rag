import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import Citations from '../Citations';

const mockCitations = [
  { filename: 'ml_guide.pdf', page_number: 3, excerpt: 'Deep learning is a subset of ML', score: 0.92 },
  { filename: 'python.pdf', page_number: 1, excerpt: 'Python is versatile', score: 0.65 },
];

describe('Citations', () => {
  it('renders nothing when citations are empty', () => {
    const { container } = render(<Citations citations={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders nothing when citations prop is undefined', () => {
    const { container } = render(<Citations citations={undefined as any} />);
    expect(container.firstChild).toBeNull();
  });

  it('shows source count in collapsed state', () => {
    render(<Citations citations={mockCitations} />);
    expect(screen.getByText('Sources (2)')).toBeInTheDocument();
  });

  it('does not show citations content when collapsed', () => {
    render(<Citations citations={mockCitations} />);
    expect(screen.queryByText('ml_guide.pdf')).not.toBeInTheDocument();
  });

  it('expands to show citation details on click', () => {
    render(<Citations citations={mockCitations} />);
    fireEvent.click(screen.getByText('Sources (2)'));

    expect(screen.getByText('ml_guide.pdf')).toBeInTheDocument();
    expect(screen.getByText('python.pdf')).toBeInTheDocument();
  });

  it('shows match percentage', () => {
    render(<Citations citations={mockCitations} />);
    fireEvent.click(screen.getByText('Sources (2)'));

    expect(screen.getByText('92% match')).toBeInTheDocument();
    expect(screen.getByText('65% match')).toBeInTheDocument();
  });

  it('shows page number when available', () => {
    render(<Citations citations={mockCitations} />);
    fireEvent.click(screen.getByText('Sources (2)'));

    expect(screen.getByText('p. 3')).toBeInTheDocument();
  });

  it('shows excerpt text', () => {
    render(<Citations citations={mockCitations} />);
    fireEvent.click(screen.getByText('Sources (2)'));

    expect(screen.getByText(/Deep learning is a subset/)).toBeInTheDocument();
  });
});
