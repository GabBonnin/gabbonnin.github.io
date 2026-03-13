import { readFileSync } from 'fs';
import { join } from 'path';
import bibtexParse from 'bibtex-parse';

export type PubType = 'journal' | 'book-chapter' | 'report' | 'thesis' | 'preprint';

export interface Publication {
  id:          string;
  title:       string;
  authors:     string;
  year:        number;
  venue:       string;
  venueShort?: string;
  type:        PubType;
  doi?:        string;
  url?:        string;
  abstract?:   string;
  order:       number;
  bibtex:      string;
}

function entryTypeToPublType(entryType: string): PubType {
  switch (entryType.toLowerCase()) {
    case 'article':       return 'journal';
    case 'incollection':
    case 'inbook':        return 'book-chapter';
    case 'techreport':
    case 'report':        return 'report';
    case 'phdthesis':
    case 'mastersthesis':
    case 'thesis':        return 'thesis';
    default:              return 'preprint';
  }
}

function formatAuthors(raw: string): string {
  if (!raw) return '';
  return raw
    .split(' and ')
    .map(a => {
      const parts = a.trim().split(',');
      if (parts.length === 2) return `${parts[0].trim()}, ${parts[1].trim()}`;
      return a.trim();
    })
    .join(', ');
}

function stripLatex(str: string): string {
  return str
    .replace(/\{\\["'](\w)\}/g, '$1')   // {\"o} → o  (simplified)
    .replace(/\\["'`^~](\w)/g, '$1')
    .replace(/\{([^}]+)\}/g, '$1')       // remove remaining braces
    .trim();
}

export function getPublications(): Publication[] {
  const bibPath = join(process.cwd(), 'publications.bib');
  const raw = readFileSync(bibPath, 'utf-8');
  const entries = bibtexParse.entries(raw);

  return entries
    .map((entry: any) => {
      // bibtex-parse returns fields as uppercase keys directly on the entry object
      const f: Record<string, string> = {};
      for (const key of Object.keys(entry)) {
        if (key !== 'key' && key !== 'type') f[key.toLowerCase()] = entry[key];
      }
      const venue =
        f.journal ?? f.booktitle ?? f.school ?? f.institution ?? '';

      const venueKey = f.journal ? 'journal'
        : f.booktitle ? 'booktitle'
        : f.school    ? 'school'
        : 'institution';

      const bibLines = [
        `@${entry.type}{${entry.key},`,
        `  title     = {${f.title ?? ''}},`,
        `  author    = {${f.author ?? ''}},`,
        `  year      = {${f.year ?? ''}},`,
        venue ? `  ${venueKey} = {${venue}},` : null,
        f.doi  ? `  doi       = {${f.doi}},`  : null,
        f.url  ? `  url       = {${f.url}},`  : null,
        `}`,
      ].filter(Boolean).join('\n');

      return {
        id:          entry.key,
        title:       stripLatex(f.title ?? ''),
        authors:     formatAuthors(stripLatex(f.author ?? '')),
        year:        parseInt(f.year ?? '0', 10),
        venue:       stripLatex(venue),
        venueShort:  f.shortjournal ? stripLatex(f.shortjournal) : undefined,
        type:        entryTypeToPublType(entry.type),
        doi:         f.doi,
        url:         f.url,
        abstract:    f.abstract ? stripLatex(f.abstract) : undefined,
        order:       parseInt(f.order ?? '99', 10),
        bibtex:      bibLines,
      } satisfies Publication;
    })
    .sort((a: Publication, b: Publication) => a.order - b.order);
}
