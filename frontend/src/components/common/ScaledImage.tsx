import React, { useState, useEffect } from 'react';
import { Image } from 'antd';

interface ScaledImageProps {
  src: string;
  alt?: string;
  maxWidth?: number;
  maxHeight?: number;
  minWidth?: number;
  minHeight?: number;
  borderRadius?: number;
  boxShadow?: string;
  style?: React.CSSProperties;
}

export const ScaledImage: React.FC<ScaledImageProps> = ({
  src,
  alt = '',
  maxWidth = 320,
  maxHeight = 240,
  minWidth = 80,
  minHeight = 60,
  borderRadius = 4,
  boxShadow = '0 2px 8px rgba(0, 0, 0, 0.1)',
  style: externalStyle = {}
}) => {
  const [dimensions, setDimensions] = useState<{ width: number; height: number }>({
    width: 0,
    height: 0
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    const img = new window.Image();
    img.src = src;
    img.onload = () => {
      const originalWidth = img.width;
      const originalHeight = img.height;
      const aspectRatio = originalWidth / originalHeight;

      let finalWidth = originalWidth;
      let finalHeight = originalHeight;

      if (originalWidth > maxWidth) {
        finalWidth = maxWidth;
        finalHeight = finalWidth / aspectRatio;
      }

      if (finalHeight > maxHeight) {
        finalHeight = maxHeight;
        finalWidth = finalHeight * aspectRatio;
      }

      if (finalWidth < minWidth) {
        finalWidth = minWidth;
        finalHeight = finalWidth / aspectRatio;
      }

      if (finalHeight < minHeight) {
        finalHeight = minHeight;
        finalWidth = finalHeight * aspectRatio;
      }

      if (finalWidth > maxWidth) {
        finalWidth = maxWidth;
        finalHeight = finalWidth / aspectRatio;
      }

      if (finalHeight > maxHeight) {
        finalHeight = maxHeight;
        finalWidth = finalHeight * aspectRatio;
      }

      setDimensions({
        width: Math.round(finalWidth),
        height: Math.round(finalHeight)
      });
      setLoading(false);
    };

    img.onerror = () => {
      setLoading(false);
    };
  }, [src, maxWidth, maxHeight, minWidth, minHeight]);

  if (loading) {
    return (
      <div
        style={{
          width: 100,
          height: 100,
          borderRadius,
          backgroundColor: '#f0f0f0',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          ...externalStyle
        }}
      >
        <span style={{ color: '#999', fontSize: 12 }}>加载中...</span>
      </div>
    );
  }

  return (
    <Image
      src={src}
      alt={alt}
      width={dimensions.width}
      height={dimensions.height}
      style={{
        objectFit: 'contain',
        borderRadius,
        boxShadow,
        transition: 'all 0.3s ease',
        ...externalStyle
      }}
    />
  );
};
