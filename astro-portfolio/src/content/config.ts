import { defineCollection, z } from 'astro:content';

const projectsCollection = defineCollection({
  type: 'content',
  schema: z.object({
    title:       z.string(),
    date:        z.string(),
    tags:        z.array(z.string()),
    description: z.string(),
    externalUrl: z.string().url().optional(),
    featured:    z.boolean().default(false),
    order:       z.number().default(99),
  }),
});

const publicationsCollection = defineCollection({
  type: 'content',
  schema: z.object({
    title:     z.string(),
    authors:   z.string(),
    year:      z.number(),
    venue:     z.string(),
    venueShort:z.string().optional(),
    type:      z.enum(['journal', 'book-chapter', 'report', 'thesis', 'preprint']),
    doi:       z.string().optional(),
    url:       z.string().url().optional(),
    abstract:  z.string().optional(),
    order:     z.number().default(99),
  }),
});

export const collections = {
  projects:     projectsCollection,
  publications: publicationsCollection,
};
