import * as React from 'react'
import { Slot } from '@radix-ui/react-slot'
import { cva, type VariantProps } from 'class-variance-authority'

import { cn } from '@/lib/utils'

const badgeVariants = cva(
  'inline-flex items-center justify-center rounded-md border px-2 py-0.5 text-xs font-medium w-fit whitespace-nowrap shrink-0 [&>svg]:size-3 gap-1 [&>svg]:pointer-events-none focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px] aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive transition-[color,box-shadow] overflow-hidden',
  {
    variants: {
      variant: {
        default:
          'border-transparent bg-[#00732a] text-[#e5f7ed] [a&]:hover:bg-[#00692a]',
        secondary:
          'border-transparent bg-[#005f4a] text-[#e5f7ed] [a&]:hover:bg-[#004f3a]',
        destructive:
          'border-transparent bg-[#cc2a1f] text-white [a&]:hover:bg-[#a61f14]',
        outline:
          'text-[#003d20] [a&]:hover:bg-[#004d30] [a&]:hover:text-[#e5f7ed]',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  },
)


function Badge({
  className,
  variant,
  asChild = false,
  ...props
}: React.ComponentProps<'span'> &
  VariantProps<typeof badgeVariants> & { asChild?: boolean }) {
  const Comp = asChild ? Slot : 'span'

  return (
    <Comp
      data-slot="badge"
      className={cn(badgeVariants({ variant }), className)}
      {...props}
    />
  )
}

export { Badge, badgeVariants }
