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

export const collections = {
  projects: projectsCollection,
};
