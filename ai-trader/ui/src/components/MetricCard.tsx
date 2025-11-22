// Metric Card Component for Dashboard
import React from 'react';
import { ArrowUpIcon, ArrowDownIcon, MinusIcon } from '@heroicons/react/24/solid';

export type TrendDirection = 'up' | 'down' | 'neutral';

interface MetricCardProps {
  title: string;
  value: string | number;
  trend?: TrendDirection;
  trendValue?: string;
  icon?: React.ReactNode;
  loading?: boolean;
  className?: string;
  valueColor?: 'default' | 'green' | 'red' | 'blue';
}

export function MetricCard({
  title,
  value,
  trend,
  trendValue,
  icon,
  loading = false,
  className = '',
  valueColor = 'default',
}: MetricCardProps) {
  const getTrendIcon = () => {
    if (!trend) return null;

    switch (trend) {
      case 'up':
        return <ArrowUpIcon className="w-4 h-4 text-green-500" />;
      case 'down':
        return <ArrowDownIcon className="w-4 h-4 text-red-500" />;
      case 'neutral':
        return <MinusIcon className="w-4 h-4 text-gray-500" />;
    }
  };

  const getTrendColor = () => {
    if (!trend) return '';

    switch (trend) {
      case 'up':
        return 'text-green-600';
      case 'down':
        return 'text-red-600';
      case 'neutral':
        return 'text-gray-600';
    }
  };

  const getValueColor = () => {
    switch (valueColor) {
      case 'green':
        return 'text-green-600';
      case 'red':
        return 'text-red-600';
      case 'blue':
        return 'text-blue-600';
      default:
        return 'text-gray-900 dark:text-gray-100';
    }
  };

  return (
    <div
      className={`bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border border-gray-200 dark:border-gray-700 ${className}`}
    >
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-medium text-gray-600 dark:text-gray-400">
          {title}
        </h3>
        {icon && (
          <div className="flex items-center justify-center w-10 h-10 rounded-full bg-blue-100 dark:bg-blue-900">
            {icon}
          </div>
        )}
      </div>

      {loading ? (
        <div className="animate-pulse">
          <div className="h-8 bg-gray-300 dark:bg-gray-600 rounded w-3/4"></div>
        </div>
      ) : (
        <>
          <div className={`text-3xl font-bold ${getValueColor()}`}>
            {value}
          </div>

          {(trend || trendValue) && (
            <div className="flex items-center mt-2 space-x-1">
              {getTrendIcon()}
              <span className={`text-sm font-medium ${getTrendColor()}`}>
                {trendValue || trend}
              </span>
            </div>
          )}
        </>
      )}
    </div>
  );
}
