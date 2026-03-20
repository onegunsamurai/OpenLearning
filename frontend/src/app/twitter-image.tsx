import {
  generateOGImage,
  ogAlt,
  ogSize,
  ogContentType,
} from "./og-shared";

export const runtime = "edge";

export const alt = ogAlt;
export const size = ogSize;
export const contentType = ogContentType;

export default async function TwitterImage() {
  return generateOGImage();
}
