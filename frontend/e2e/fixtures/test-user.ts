export const TEST_USER = {
  email: process.env.E2E_TEST_EMAIL ?? "",
  password: process.env.E2E_TEST_PASSWORD ?? "",
} as const;
