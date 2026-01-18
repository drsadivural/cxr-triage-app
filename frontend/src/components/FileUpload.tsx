'use client';

import { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { CloudArrowUpIcon, DocumentIcon } from '@heroicons/react/24/outline';
import clsx from 'clsx';

interface FileUploadProps {
  onFileSelect: (file: File) => void;
  isLoading?: boolean;
  accept?: Record<string, string[]>;
}

export default function FileUpload({
  onFileSelect,
  isLoading = false,
  accept = {
    'application/dicom': ['.dcm', '.dicom'],
    'image/png': ['.png'],
    'image/jpeg': ['.jpg', '.jpeg'],
  },
}: FileUploadProps) {
  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      if (acceptedFiles.length > 0) {
        onFileSelect(acceptedFiles[0]);
      }
    },
    [onFileSelect]
  );

  const { getRootProps, getInputProps, isDragActive, acceptedFiles } = useDropzone({
    onDrop,
    accept,
    multiple: false,
    disabled: isLoading,
  });

  return (
    <div
      {...getRootProps()}
      className={clsx(
        'border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors',
        isDragActive
          ? 'border-primary-500 bg-primary-50'
          : 'border-gray-300 hover:border-primary-400 hover:bg-gray-50',
        isLoading && 'opacity-50 cursor-not-allowed'
      )}
    >
      <input {...getInputProps()} />

      <div className="flex flex-col items-center">
        {isLoading ? (
          <>
            <div className="w-12 h-12 spinner mb-4" />
            <p className="text-gray-600">Analyzing image...</p>
          </>
        ) : acceptedFiles.length > 0 ? (
          <>
            <DocumentIcon className="w-12 h-12 text-primary-500 mb-4" />
            <p className="text-gray-900 font-medium">{acceptedFiles[0].name}</p>
            <p className="text-gray-500 text-sm mt-1">
              {(acceptedFiles[0].size / 1024 / 1024).toFixed(2)} MB
            </p>
            <p className="text-primary-600 text-sm mt-2">
              Drop another file to replace
            </p>
          </>
        ) : (
          <>
            <CloudArrowUpIcon className="w-12 h-12 text-gray-400 mb-4" />
            <p className="text-gray-600">
              {isDragActive ? (
                'Drop the file here...'
              ) : (
                <>
                  <span className="text-primary-600 font-medium">
                    Click to upload
                  </span>{' '}
                  or drag and drop
                </>
              )}
            </p>
            <p className="text-gray-400 text-sm mt-2">
              DICOM, PNG, or JPEG (max 50MB)
            </p>
          </>
        )}
      </div>
    </div>
  );
}
